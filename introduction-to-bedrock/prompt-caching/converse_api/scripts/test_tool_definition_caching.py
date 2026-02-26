"""
Test script for Amazon Bedrock Prompt Caching - Tool Definition Checkpoints
Tests 2 APIs: ConverseStream, Converse

Demonstrates caching tool definitions for agentic applications. Useful when you
have a large, static set of tools that don't change between requests but the
user queries vary.

"""

import boto3
import json
import time
import argparse

# ============================================================================
# CONFIGURATION - Modify these values as needed
# ============================================================================
MODEL_ID = "global.anthropic.claude-sonnet-4-6-v1:0"
AWS_PROFILE = "default"
AWS_REGION = "us-west-2"
CACHE_TTL = "5m"

# ============================================================================
# TOOL DEFINITIONS - Space-themed tools with comprehensive schemas (>1,024 tokens)
# ============================================================================

TOOL_ANALYZE_CELESTIAL_OBJECT = {
    "name": "analyze_celestial_object",
    "description": "Analyzes a celestial object and returns detailed information about its physical properties, composition, and characteristics. Use this tool when you need comprehensive data about planets, moons, stars, asteroids, or other celestial bodies. The tool queries astronomical databases and returns structured information suitable for scientific analysis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "object_name": {
                "type": "string",
                "description": "The name or designation of the celestial object to analyze (e.g., 'Mars', 'Europa', 'Proxima Centauri b', 'Ceres')"
            },
            "object_type": {
                "type": "string",
                "enum": ["planet", "dwarf_planet", "moon", "asteroid", "comet", "star", "exoplanet", "nebula", "galaxy"],
                "description": "The classification of the celestial object"
            },
            "analysis_depth": {
                "type": "string",
                "enum": ["basic", "standard", "comprehensive"],
                "description": "Level of detail for the analysis. Basic includes mass, diameter, and orbit. Standard adds composition and atmosphere. Comprehensive includes geological features, magnetic field, and habitability assessment."
            },
            "include_moons": {
                "type": "boolean",
                "description": "Whether to include information about the object's natural satellites (if applicable)"
            },
            "coordinate_system": {
                "type": "string",
                "enum": ["ecliptic", "equatorial", "galactic"],
                "description": "The coordinate system to use for positional data"
            },
            "epoch": {
                "type": "string",
                "description": "The reference epoch for orbital elements (e.g., 'J2000', '2024-01-01')"
            },
            "output_units": {
                "type": "object",
                "properties": {
                    "mass": {
                        "type": "string",
                        "enum": ["kg", "earth_masses", "solar_masses", "jupiter_masses"],
                        "description": "Unit for mass measurements"
                    },
                    "distance": {
                        "type": "string",
                        "enum": ["km", "au", "light_years", "parsecs"],
                        "description": "Unit for distance measurements"
                    },
                    "temperature": {
                        "type": "string",
                        "enum": ["kelvin", "celsius", "fahrenheit"],
                        "description": "Unit for temperature measurements"
                    }
                },
                "description": "Preferred units for output measurements"
            }
        },
        "required": ["object_name", "object_type"]
    }
}

TOOL_CALCULATE_ORBITAL_MECHANICS = {
    "name": "calculate_orbital_mechanics",
    "description": "Performs orbital mechanics calculations including trajectory planning, orbital transfers, gravitational interactions, and mission feasibility assessments. Essential for spacecraft mission planning and understanding celestial body dynamics. Supports both two-body and n-body calculations depending on accuracy requirements.",
    "input_schema": {
        "type": "object",
        "properties": {
            "calculation_type": {
                "type": "string",
                "enum": ["hohmann_transfer", "gravity_assist", "orbital_period", "escape_velocity", "delta_v", "sphere_of_influence", "lagrange_points", "orbital_decay"],
                "description": "The type of orbital calculation to perform"
            },
            "origin_body": {
                "type": "string",
                "description": "The starting celestial body or orbit (e.g., 'Earth', 'LEO', 'Earth-Moon L2')"
            },
            "destination_body": {
                "type": "string",
                "description": "The target celestial body or orbit"
            },
            "orbital_elements": {
                "type": "object",
                "properties": {
                    "semi_major_axis": {
                        "type": "number",
                        "description": "Semi-major axis of the orbit in kilometers"
                    },
                    "eccentricity": {
                        "type": "number",
                        "description": "Orbital eccentricity (0 for circular, 0-1 for elliptical)"
                    },
                    "inclination": {
                        "type": "number",
                        "description": "Orbital inclination in degrees"
                    },
                    "longitude_ascending_node": {
                        "type": "number",
                        "description": "Longitude of the ascending node in degrees"
                    },
                    "argument_periapsis": {
                        "type": "number",
                        "description": "Argument of periapsis in degrees"
                    },
                    "true_anomaly": {
                        "type": "number",
                        "description": "True anomaly at epoch in degrees"
                    }
                },
                "description": "Keplerian orbital elements for custom orbit calculations"
            },
            "spacecraft_mass": {
                "type": "number",
                "description": "Mass of the spacecraft in kilograms (required for delta-v calculations)"
            },
            "propulsion_system": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["chemical", "ion", "nuclear_thermal", "solar_sail"],
                        "description": "Type of propulsion system"
                    },
                    "specific_impulse": {
                        "type": "number",
                        "description": "Specific impulse (Isp) in seconds"
                    },
                    "thrust": {
                        "type": "number",
                        "description": "Maximum thrust in Newtons"
                    }
                },
                "description": "Propulsion system characteristics"
            },
            "launch_window": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start of launch window search (ISO 8601 format)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of launch window search (ISO 8601 format)"
                    },
                    "optimization_criteria": {
                        "type": "string",
                        "enum": ["minimum_delta_v", "minimum_time", "balanced"],
                        "description": "What to optimize for when calculating launch windows"
                    }
                },
                "description": "Launch window parameters"
            }
        },
        "required": ["calculation_type", "origin_body"]
    }
}

TOOL_SEARCH_EXOPLANET_DATABASE = {
    "name": "search_exoplanet_database",
    "description": "Searches comprehensive exoplanet databases including NASA Exoplanet Archive and EU Exoplanet Catalogue. Returns detailed information about confirmed exoplanets, their host stars, detection methods, and habitability assessments. Supports complex queries with multiple filter criteria.",
    "input_schema": {
        "type": "object",
        "properties": {
            "search_mode": {
                "type": "string",
                "enum": ["by_name", "by_star", "by_criteria", "by_region"],
                "description": "The search mode to use"
            },
            "planet_name": {
                "type": "string",
                "description": "Specific planet name or designation (e.g., 'Kepler-442b', 'TRAPPIST-1e')"
            },
            "host_star": {
                "type": "string",
                "description": "Name of the host star to search for planets around"
            },
            "discovery_method": {
                "type": "string",
                "enum": ["transit", "radial_velocity", "direct_imaging", "microlensing", "timing", "astrometry"],
                "description": "Filter by discovery method"
            },
            "mass_range": {
                "type": "object",
                "properties": {
                    "min": {
                        "type": "number",
                        "description": "Minimum mass in Earth masses"
                    },
                    "max": {
                        "type": "number",
                        "description": "Maximum mass in Earth masses"
                    }
                },
                "description": "Filter by planetary mass range"
            },
            "radius_range": {
                "type": "object",
                "properties": {
                    "min": {
                        "type": "number",
                        "description": "Minimum radius in Earth radii"
                    },
                    "max": {
                        "type": "number",
                        "description": "Maximum radius in Earth radii"
                    }
                },
                "description": "Filter by planetary radius range"
            },
            "orbital_period_range": {
                "type": "object",
                "properties": {
                    "min": {
                        "type": "number",
                        "description": "Minimum orbital period in Earth days"
                    },
                    "max": {
                        "type": "number",
                        "description": "Maximum orbital period in Earth days"
                    }
                },
                "description": "Filter by orbital period range"
            },
            "habitable_zone_only": {
                "type": "boolean",
                "description": "Only return planets within the habitable zone of their host star"
            },
            "equilibrium_temperature_range": {
                "type": "object",
                "properties": {
                    "min": {
                        "type": "number",
                        "description": "Minimum equilibrium temperature in Kelvin"
                    },
                    "max": {
                        "type": "number",
                        "description": "Maximum equilibrium temperature in Kelvin"
                    }
                },
                "description": "Filter by planetary equilibrium temperature"
            },
            "stellar_type": {
                "type": "string",
                "enum": ["O", "B", "A", "F", "G", "K", "M"],
                "description": "Filter by host star spectral type"
            },
            "distance_from_earth": {
                "type": "object",
                "properties": {
                    "max_light_years": {
                        "type": "number",
                        "description": "Maximum distance from Earth in light years"
                    }
                },
                "description": "Filter by distance from Earth"
            },
            "sort_by": {
                "type": "string",
                "enum": ["distance", "mass", "radius", "discovery_date", "habitability_score"],
                "description": "Field to sort results by"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return"
            }
        },
        "required": ["search_mode"]
    }
}

TOOL_SIMULATE_MISSION_TRAJECTORY = {
    "name": "simulate_mission_trajectory",
    "description": "Simulates complete spacecraft mission trajectories from launch to destination arrival. Includes multi-body gravitational effects, maneuver planning, and mission phase modeling. Provides detailed timeline, fuel consumption, and trajectory visualization data. Used for mission planning and feasibility studies.",
    "input_schema": {
        "type": "object",
        "properties": {
            "mission_name": {
                "type": "string",
                "description": "Name identifier for this mission simulation"
            },
            "mission_type": {
                "type": "string",
                "enum": ["flyby", "orbiter", "lander", "sample_return", "crewed", "telescope"],
                "description": "The type of mission being simulated"
            },
            "launch_site": {
                "type": "string",
                "enum": ["kennedy_space_center", "vandenberg", "baikonur", "kourou", "tanegashima", "satish_dhawan", "cape_canaveral"],
                "description": "Launch facility location"
            },
            "launch_date": {
                "type": "string",
                "description": "Planned launch date in ISO 8601 format"
            },
            "target_body": {
                "type": "string",
                "description": "The destination celestial body"
            },
            "gravity_assists": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "body": {
                            "type": "string",
                            "description": "Planet or moon for gravity assist"
                        },
                        "approach_altitude": {
                            "type": "number",
                            "description": "Closest approach altitude in kilometers"
                        },
                        "expected_date": {
                            "type": "string",
                            "description": "Expected flyby date"
                        }
                    }
                },
                "description": "Sequence of gravity assist maneuvers"
            },
            "spacecraft_configuration": {
                "type": "object",
                "properties": {
                    "dry_mass": {
                        "type": "number",
                        "description": "Spacecraft dry mass in kilograms"
                    },
                    "fuel_mass": {
                        "type": "number",
                        "description": "Propellant mass in kilograms"
                    },
                    "power_system": {
                        "type": "string",
                        "enum": ["solar_panels", "rtg", "nuclear_reactor", "battery"],
                        "description": "Primary power generation system"
                    },
                    "communication_band": {
                        "type": "string",
                        "enum": ["S_band", "X_band", "Ka_band", "optical"],
                        "description": "Primary communication frequency band"
                    }
                },
                "description": "Spacecraft technical specifications"
            },
            "simulation_parameters": {
                "type": "object",
                "properties": {
                    "time_step": {
                        "type": "number",
                        "description": "Integration time step in seconds"
                    },
                    "include_perturbations": {
                        "type": "boolean",
                        "description": "Include gravitational perturbations from other bodies"
                    },
                    "include_solar_pressure": {
                        "type": "boolean",
                        "description": "Include solar radiation pressure effects"
                    },
                    "monte_carlo_runs": {
                        "type": "integer",
                        "description": "Number of Monte Carlo runs for uncertainty analysis"
                    }
                },
                "description": "Simulation accuracy and fidelity parameters"
            },
            "output_format": {
                "type": "string",
                "enum": ["summary", "detailed", "trajectory_data", "visualization"],
                "description": "Format of simulation output"
            }
        },
        "required": ["mission_name", "mission_type", "launch_date", "target_body"]
    }
}

TOOLS_LIST = [
    TOOL_ANALYZE_CELESTIAL_OBJECT,
    TOOL_CALCULATE_ORBITAL_MECHANICS,
    TOOL_SEARCH_EXOPLANET_DATABASE,
    TOOL_SIMULATE_MISSION_TRAJECTORY
]

QUESTION_PROMPT = "I want to plan a mission to Europa. Can you help me understand if it's feasible and what tools you'd use?"


def create_bedrock_client():
    """Create a Bedrock Runtime client with the specified profile and region."""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return session.client("bedrock-runtime")


def build_converse_tools():
    """Build tools for Converse API with cache checkpoint."""
    tools = []
    for tool in TOOLS_LIST:
        tools.append({
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": tool["input_schema"]
                }
            }
        })
    tools.append({"cachePoint": {"type": "default"}})
    return tools


def test_converse_stream_tools(client):
    """Test tool definition caching with ConverseStream API."""
    print("\n" + "=" * 60)
    print("Test 1: ConverseStream (tool definitions)")
    print("=" * 60)

    results = {"first": {}, "second": {}}

    for attempt, label in [(1, "first"), (2, "second")]:
        print(f"\nRequest {attempt} ({'cache write expected' if attempt == 1 else 'cache read expected'})...")

        response = client.converse_stream(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": QUESTION_PROMPT}]
                }
            ],
            toolConfig={
                "tools": build_converse_tools()
            },
            inferenceConfig={
                "maxTokens": 512
            }
        )

        response_text = ""
        usage_data = {}

        for event in response["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    response_text += delta["text"]
            elif "metadata" in event:
                usage_data = event["metadata"].get("usage", {})

        results[label] = {
            "cache_write": usage_data.get("cacheWriteInputTokens", 0),
            "cache_read": usage_data.get("cacheReadInputTokens", 0),
            "input_tokens": usage_data.get("inputTokens", 0),
            "output_tokens": usage_data.get("outputTokens", 0)
        }

        print(f"  Input tokens: {results[label]['input_tokens']}")
        print(f"  Output tokens: {results[label]['output_tokens']}")
        print(f"  CacheWriteInputTokens: {results[label]['cache_write']}")
        print(f"  CacheReadInputTokens: {results[label]['cache_read']}")

        if attempt == 1:
            time.sleep(1)

    first_cache_activity = results["first"]["cache_write"] > 0 or results["first"]["cache_read"] > 0
    second_cache_read = results["second"]["cache_read"] > 0
    passed = first_cache_activity and second_cache_read
    status = "PASSED" if passed else "FAILED"
    print(f"\n{'✓' if passed else '✗'} {status}: {'Cache checkpoint working correctly' if passed else 'Cache not working as expected'}")

    return passed


def test_converse_tools(client):
    """Test tool definition caching with Converse API."""
    print("\n" + "=" * 60)
    print("Test 2: Converse (tool definitions)")
    print("=" * 60)

    results = {"first": {}, "second": {}}

    for attempt, label in [(1, "first"), (2, "second")]:
        print(f"\nRequest {attempt} ({'cache write expected' if attempt == 1 else 'cache read expected'})...")

        response = client.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": QUESTION_PROMPT}]
                }
            ],
            toolConfig={
                "tools": build_converse_tools()
            },
            inferenceConfig={
                "maxTokens": 512
            }
        )

        usage_data = response.get("usage", {})

        results[label] = {
            "cache_write": usage_data.get("cacheWriteInputTokens", 0),
            "cache_read": usage_data.get("cacheReadInputTokens", 0),
            "input_tokens": usage_data.get("inputTokens", 0),
            "output_tokens": usage_data.get("outputTokens", 0),
            "cache_details": usage_data.get("cacheDetails", [])
        }

        print(f"  Input tokens: {results[label]['input_tokens']}")
        print(f"  Output tokens: {results[label]['output_tokens']}")
        print(f"  CacheWriteInputTokens: {results[label]['cache_write']}")
        print(f"  CacheReadInputTokens: {results[label]['cache_read']}")
        if results[label]["cache_details"]:
            print(f"  CacheDetails (tokens per TTL):")
            for detail in results[label]["cache_details"]:
                print(f"    - TTL {detail['ttl']}: {detail['inputTokens']} tokens")

        if attempt == 1:
            time.sleep(1)

    first_cache_activity = results["first"]["cache_write"] > 0 or results["first"]["cache_read"] > 0
    second_cache_read = results["second"]["cache_read"] > 0
    passed = first_cache_activity and second_cache_read
    status = "PASSED" if passed else "FAILED"
    print(f"\n{'✓' if passed else '✗'} {status}: {'Cache checkpoint working correctly' if passed else 'Cache not working as expected'}")

    return passed


def main():
    """Run all tool definition caching tests."""
    parser = argparse.ArgumentParser(
        description="Test Amazon Bedrock Prompt Caching - Tool Definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This test demonstrates caching tool definitions for agentic applications.
The tool schemas are cached and reused across multiple requests with
different user queries, reducing latency and costs for tool-heavy workloads.

Examples:
  python test_tool_definition_caching.py
        """
    )
    parser.parse_args()

    print("=" * 60)
    print("Testing Tool Definition Caching with Amazon Bedrock")
    print("=" * 60)
    print(f"Model: {MODEL_ID}")
    print(f"Region: {AWS_REGION}")
    print(f"Profile: {AWS_PROFILE}")
    print(f"Cache TTL: {CACHE_TTL}")
    print(f"Checkpoint Type: Tool Definitions")
    print(f"Number of Tools: {len(TOOLS_LIST)}")

    client = create_bedrock_client()

    results = {}

    results["ConverseStream"] = test_converse_stream_tools(client)
    results["Converse"] = test_converse_tools(client)

    print("\n" + "=" * 60)
    print("SUMMARY (tool definition caching)")
    print("=" * 60)

    all_passed = True
    for api, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {api}: {status}")
        if not passed:
            all_passed = False

    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
