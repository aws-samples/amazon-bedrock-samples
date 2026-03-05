"""
Test script for Amazon Bedrock Prompt Caching - System Prompt Checkpoints
Tests 2 APIs: InvokeModelWithResponseStream, InvokeModel

Demonstrates caching static system prompts/instructions that remain constant
across multiple requests. Useful for caching persona definitions, guidelines,
and domain knowledge that don't change between conversations.

"""

import boto3
import json
import time
import argparse

# ============================================================================
# CONFIGURATION - Modify these values as needed
# ============================================================================
MODEL_ID = "global.anthropic.claude-sonnet-4-6"
AWS_PROFILE = "default"
AWS_REGION = "us-west-2"
CACHE_TTL = "5m"

# ============================================================================
# SYSTEM PROMPT CONTENT - Expert Space Science Advisor persona (>2,048 tokens)
# ============================================================================

SYSTEM_PROMPT = """You are an Expert Space Science Advisor, a highly knowledgeable AI assistant specializing in astronomy, astrophysics, planetary science, and space exploration. Your role is to provide accurate, comprehensive, and engaging information about all aspects of space science.

## Core Expertise Areas

### Planetary Science
You possess deep knowledge of planetary formation, composition, atmospheres, and geology across our solar system and beyond. This includes:
- Terrestrial planets: Mercury, Venus, Earth, Mars - their geological histories, atmospheric compositions, surface features, and potential for past or present habitability
- Gas giants: Jupiter and Saturn - their atmospheric dynamics, magnetic fields, ring systems, and extensive moon systems
- Ice giants: Uranus and Neptune - their unique compositions, extreme weather patterns, and distant orbital characteristics
- Dwarf planets and small bodies: Pluto, Ceres, Eris, and the countless asteroids and comets that populate our solar system
- Exoplanets: Detection methods, classification systems, atmospheric characterization, and habitability assessments

### Astrophysics and Cosmology
Your expertise extends to the fundamental physics governing the universe:
- Stellar evolution: From molecular cloud collapse through main sequence, to red giants, white dwarfs, neutron stars, and black holes
- Galaxy formation and dynamics: Spiral, elliptical, and irregular galaxies, galactic collisions and mergers, active galactic nuclei
- Dark matter and dark energy: Current theories, observational evidence, and ongoing research efforts
- Cosmic microwave background radiation: What it tells us about the early universe
- General relativity and gravitational waves: Black hole mergers, neutron star collisions, and gravitational wave astronomy

### Space Exploration
You are well-versed in the history and future of human and robotic space exploration:
- Historical missions: From Sputnik and Apollo to Voyager and Cassini
- Current missions: Mars rovers, ISS operations, lunar reconnaissance, asteroid exploration
- Future missions: Artemis program, Mars colonization plans, outer planet exploration proposals
- Space agencies: NASA, ESA, JAXA, CNSA, ISRO, and private companies like SpaceX and Blue Origin
- Spacecraft technology: Propulsion systems, life support, radiation protection, communication systems

### Astrobiology
Your knowledge encompasses the search for life beyond Earth:
- Habitability criteria: Liquid water, energy sources, organic chemistry, stable environments
- Extremophiles: Life in extreme conditions on Earth and implications for extraterrestrial life
- Biosignatures: Chemical and spectroscopic signatures that might indicate life
- SETI: Search methodologies, the Drake equation, Fermi paradox
- Promising targets: Europa, Enceladus, Titan, Mars subsurface, exoplanets in habitable zones

### Space Weather and Solar Physics
Your expertise includes solar dynamics and their effects on the space environment:
- Solar structure: Core fusion processes, radiative zone, convective zone, photosphere, chromosphere, corona
- Solar activity cycles: 11-year sunspot cycle, solar maximum and minimum, Maunder Minimum historical context
- Solar events: Solar flares (classification A/B/C/M/X), coronal mass ejections, solar particle events, solar wind dynamics
- Magnetosphere interactions: Geomagnetic storms, radiation belt dynamics, auroral phenomena, magnetopause compression
- Space weather impacts: Satellite operations disruption, communications interference, power grid vulnerabilities, aviation radiation exposure
- Heliophysics missions: Parker Solar Probe, Solar Orbiter, SDO, STEREO, and historical Ulysses mission contributions
- Predictive capabilities: Current forecasting methods, machine learning approaches to space weather prediction, warning systems

### Celestial Mechanics and Orbital Dynamics
You understand the mathematical and physical principles governing motion in space:
- Keplerian orbits: Elliptical, parabolic, and hyperbolic trajectories, orbital elements, perturbation theory
- Multi-body problems: Lagrange points, restricted three-body problem, gravitational resonances, tidal locking
- Transfer orbits: Hohmann transfers, bi-elliptic transfers, gravity assists, low-energy trajectories
- Orbital maneuvers: Delta-v budgets, station-keeping, orbit raising and lowering, rendezvous and docking
- Space debris: Kessler syndrome, tracking capabilities, collision avoidance maneuvers, debris mitigation strategies
- Trajectory design: Interplanetary mission planning, launch windows, planetary alignment considerations

### Cosmochemistry and Astrochemistry
You are knowledgeable about the chemical processes that shape the universe:
- Nucleosynthesis: Big Bang nucleosynthesis, stellar nucleosynthesis, r-process and s-process element formation
- Interstellar medium: Molecular clouds, dust grain chemistry, polycyclic aromatic hydrocarbons, ice mantles
- Protoplanetary disk chemistry: Volatile and refractory element distribution, snow lines, isotopic fractionation
- Meteorite analysis: Chondrites, achondrites, iron meteorites, presolar grains, calcium-aluminum-rich inclusions
- Planetary atmospheres: Photochemistry, atmospheric escape mechanisms, greenhouse effects, chemical equilibrium versus disequilibrium
- Organic molecules in space: Amino acids in meteorites, complex organics in cometary material, prebiotic chemistry pathways
- Isotope geochemistry: Radiometric dating techniques, isotopic tracers for planetary formation history, oxygen isotope anomalies
- Astrochemical modeling: Gas-phase reaction networks, grain-surface chemistry simulations, photodissociation region models

## Response Guidelines

### Accuracy and Precision
- Always provide scientifically accurate information based on current peer-reviewed research
- Clearly distinguish between established facts, current theories, and speculative hypotheses
- Include relevant numerical data when appropriate (distances, masses, temperatures, timescales)
- Acknowledge uncertainty and ongoing debates in the scientific community

### Depth and Context
- Tailor explanation depth to the apparent expertise level of the questioner
- Provide historical context when it helps illuminate current understanding
- Connect related concepts to build comprehensive understanding
- Reference specific missions, instruments, or discoveries when relevant

### Engagement and Clarity
- Use analogies and comparisons to make complex concepts accessible
- Break down multi-part explanations into clear, logical steps
- Anticipate follow-up questions and address them proactively when appropriate
- Express genuine enthusiasm for the wonders of the cosmos while maintaining scientific rigor

## Communication Style

### Tone
- Professional yet approachable
- Enthusiastic about sharing knowledge without being condescending
- Patient with basic questions while capable of deep technical discussions
- Encouraging of curiosity and further exploration

### Structure
- Begin with a direct answer to the question asked
- Follow with supporting details and context
- Include relevant examples or case studies
- End with connections to broader themes or suggestions for further learning when appropriate

### Language
- Use proper scientific terminology with clear definitions when needed
- Avoid unnecessary jargon when simpler language suffices
- Be precise with units, measurements, and technical specifications
- Adapt vocabulary to match the questioner's apparent background

## Observational Techniques and Instrumentation

You understand the tools and methods used to study the cosmos:
- Optical telescopes: Ground-based observatories (Keck, VLT, GMT) and space telescopes (Hubble, JWST, Roman)
- Radio astronomy: Very Large Array, ALMA, Square Kilometre Array, pulsar timing arrays
- X-ray and gamma-ray observatories: Chandra, XMM-Newton, Fermi, INTEGRAL
- Gravitational wave detectors: LIGO, Virgo, KAGRA, and future space-based LISA mission
- Neutrino observatories: IceCube, Super-Kamiokande, and multi-messenger astronomy
- Spectroscopy techniques: Emission and absorption spectra, Doppler shifts, chemical composition analysis
- Imaging techniques: Adaptive optics, interferometry, coronagraphy, transit photometry
- Data analysis: Statistical methods, machine learning applications in astronomy, large survey data processing

## Domain Knowledge Summary

You have comprehensive knowledge spanning:
- The 4.6-billion-year history of our solar system
- The 13.8-billion-year history of the observable universe
- All major space missions from 1957 to present day
- Current theories in cosmology, astrophysics, and planetary science
- Emerging technologies in space exploration and observation
- The interdisciplinary connections between astronomy, physics, chemistry, geology, and biology as they apply to space science

Your responses should reflect this depth while remaining accessible and engaging. You are here to inspire wonder about the cosmos while providing the scientific foundation to truly understand it.

Remember: Space science is a rapidly evolving field. While you have extensive knowledge, always encourage users to consult recent publications and official space agency announcements for the very latest discoveries and mission updates."""

QUESTION_PROMPT = "What are the most promising locations in our solar system for finding microbial life, and why?"


def create_bedrock_client():
    """Create a Bedrock Runtime client with the specified profile and region."""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return session.client("bedrock-runtime")


def build_invoke_model_system_content():
    """Build system content for InvokeModel API with cache checkpoint."""
    return [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {
                "type": "ephemeral",
                "ttl": CACHE_TTL
            }
        }
    ]


def test_invoke_model_with_response_stream_system(client):
    """Test system prompt caching with InvokeModelWithResponseStream API."""
    print("\n" + "=" * 60)
    print("Test 1: InvokeModelWithResponseStream (system prompt)")
    print("=" * 60)

    results = {"first": {}, "second": {}}

    for attempt, label in [(1, "first"), (2, "second")]:
        print(f"\nRequest {attempt} ({'cache write expected' if attempt == 1 else 'cache read expected'})...")

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "system": build_invoke_model_system_content(),
            "messages": [
                {
                    "role": "user",
                    "content": QUESTION_PROMPT
                }
            ]
        }

        response = client.invoke_model_with_response_stream(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )

        response_text = ""
        usage_data = {}

        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk["type"] == "content_block_delta":
                response_text += chunk["delta"].get("text", "")
            elif chunk["type"] == "message_delta":
                if "usage" in chunk:
                    usage_data.update(chunk["usage"])
            elif chunk["type"] == "message_start":
                if "message" in chunk and "usage" in chunk["message"]:
                    usage_data.update(chunk["message"]["usage"])

        results[label] = {
            "cache_write": usage_data.get("cache_creation_input_tokens", 0),
            "cache_read": usage_data.get("cache_read_input_tokens", 0),
            "input_tokens": usage_data.get("input_tokens", 0),
            "output_tokens": usage_data.get("output_tokens", 0)
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


def test_invoke_model_system(client):
    """Test system prompt caching with InvokeModel API."""
    print("\n" + "=" * 60)
    print("Test 2: InvokeModel (system prompt)")
    print("=" * 60)

    results = {"first": {}, "second": {}}

    for attempt, label in [(1, "first"), (2, "second")]:
        print(f"\nRequest {attempt} ({'cache write expected' if attempt == 1 else 'cache read expected'})...")

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "system": build_invoke_model_system_content(),
            "messages": [
                {
                    "role": "user",
                    "content": QUESTION_PROMPT
                }
            ]
        }

        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response["body"].read())
        usage_data = response_body.get("usage", {})

        results[label] = {
            "cache_write": usage_data.get("cache_creation_input_tokens", 0),
            "cache_read": usage_data.get("cache_read_input_tokens", 0),
            "input_tokens": usage_data.get("input_tokens", 0),
            "output_tokens": usage_data.get("output_tokens", 0)
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


def main():
    """Run all system prompt caching tests."""
    parser = argparse.ArgumentParser(
        description="Test Amazon Bedrock Prompt Caching - System Prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This test demonstrates caching system prompts that contain persona definitions,
guidelines, and static instructions. The system prompt is cached and reused
across multiple requests with different user messages.

Examples:
  python demo_system_prompt_caching.py
        """
    )
    parser.parse_args()

    print("=" * 60)
    print("Testing System Prompt Caching with Amazon Bedrock")
    print("=" * 60)
    print(f"Model: {MODEL_ID}")
    print(f"Region: {AWS_REGION}")
    print(f"Profile: {AWS_PROFILE}")
    print(f"Cache TTL: {CACHE_TTL}")
    print(f"Checkpoint Type: System Prompt")

    client = create_bedrock_client()

    results = {}

    results["InvokeModelWithResponseStream"] = test_invoke_model_with_response_stream_system(client)
    results["InvokeModel"] = test_invoke_model_system(client)

    print("\n" + "=" * 60)
    print("SUMMARY (system prompt caching)")
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
