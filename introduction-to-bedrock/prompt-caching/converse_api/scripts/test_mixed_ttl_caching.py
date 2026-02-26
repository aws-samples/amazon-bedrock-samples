"""
Test script for Amazon Bedrock Prompt Caching - Mixed TTL Checkpoints
Tests 2 APIs: ConverseStream, Converse

Demonstrates mixed-TTL cache checkpoints in a single request and displays the
per-TTL breakdown from the cacheDetails response field. Only tests Converse APIs
because InvokeModel does not return cacheDetails.

Notes:
- Longer TTL checkpoints must come before shorter TTL checkpoints (API constraint)
- cacheDetails is returned by Converse but NOT by ConverseStream
- Each cache checkpoint requires >=1,024 tokens (Claude Sonnet 4.6)

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

# Two TTL values for mixed-TTL demo (longer TTL must come first)
CACHE_TTL_LONG = "1h"
CACHE_TTL_SHORT = "5m"

# ============================================================================
# SAMPLE TEXT - Space-themed content split into 2 sections for cache checkpoints
# Each section combines 2 sub-sections to exceed 1,024 tokens per checkpoint
# (minimum for Claude Sonnet 4.6)
# ============================================================================

# Section 1: Inner + Outer Solar System (cached at 1h TTL)
SPACE_SECTION_1 = """
The universe is a vast and mysterious expanse that has captivated human imagination for millennia. From the earliest civilizations who looked up at the night sky and wondered about the nature of the stars, to modern astronomers using sophisticated telescopes and spacecraft to explore distant galaxies, our quest to understand the cosmos continues unabated.

Our solar system, located in the Milky Way galaxy, is home to eight planets, numerous dwarf planets, and countless smaller objects including asteroids, comets, and meteoroids. The Sun, a middle-aged G-type main-sequence star, provides the energy that sustains life on Earth and influences the dynamics of all objects within its gravitational reach.

Mercury, the innermost planet, experiences extreme temperature variations due to its proximity to the Sun and lack of substantial atmosphere. Venus, often called Earth's twin due to its similar size, has a thick atmosphere composed primarily of carbon dioxide, creating a runaway greenhouse effect that makes it the hottest planet in our solar system. Earth, our home, is the only known planet to harbor life, with its unique combination of liquid water, moderate temperatures, and protective magnetic field.

Mars, the Red Planet, has long been a subject of fascination and speculation about the possibility of extraterrestrial life. Its rusty appearance comes from iron oxide prevalent on its surface. The planet features the largest volcano in the solar system, Olympus Mons, and a canyon system, Valles Marineris, that dwarfs the Grand Canyon. Recent Mars missions have discovered evidence of ancient river systems and the presence of water ice beneath the surface.

The asteroid belt, located between Mars and Jupiter, contains millions of rocky objects ranging from small boulders to the dwarf planet Ceres. These remnants from the early solar system provide valuable insights into planetary formation and the conditions that existed billions of years ago. Scientists study these asteroids to understand the building blocks of planets and the early solar system's chemical composition. Some asteroids contain valuable metals and minerals that may one day be mined for space-based industries.

The terrestrial planets share common characteristics: rocky compositions, relatively small sizes compared to gas giants, and solid surfaces. Mercury's heavily cratered surface resembles our Moon, preserving a record of impacts from the early solar system. Venus's dense atmosphere traps heat so effectively that its surface temperature exceeds that of Mercury, despite being farther from the Sun. Earth's plate tectonics continuously reshape its surface, while Mars shows evidence of past geological activity including ancient volcanoes and water-carved channels.

Jupiter, the largest planet, is a gas giant composed primarily of hydrogen and helium. Its Great Red Spot, a persistent anticyclonic storm, has been observed for over 400 years. Jupiter's intense magnetic field and numerous moons, including the four Galilean satellites discovered by Galileo Galilei in 1610, make it a miniature solar system in its own right. Europa, one of these moons, is believed to have a subsurface ocean that could potentially harbor life.

Saturn, famous for its spectacular ring system, is another gas giant with dozens of moons. Titan, its largest moon, has a thick atmosphere and liquid hydrocarbon lakes, making it one of the most intriguing bodies in the solar system for astrobiological research. The Cassini-Huygens mission provided unprecedented details about Saturn and its moons during its 13-year exploration.

Uranus and Neptune, the ice giants, reside in the outer reaches of our solar system. Uranus rotates on its side, likely due to a massive impact early in its history. Neptune, the windiest planet, features storms with wind speeds exceeding 2,000 kilometers per hour. Both planets have ring systems, though less prominent than Saturn's.

Beyond Neptune lies the Kuiper Belt, a region populated by icy bodies including the dwarf planet Pluto. The New Horizons mission's flyby of Pluto in 2015 revealed a geologically active world with nitrogen glaciers and a hazy atmosphere. Even further out is the Oort Cloud, a hypothetical spherical shell of icy objects that may extend halfway to the nearest star.

The outer solar system remains largely unexplored compared to the inner planets. Only Voyager 2 has visited both Uranus and Neptune, conducting brief flybys in the 1980s. Future missions are being planned to study these ice giants in more detail, potentially including orbiters and atmospheric probes. The moons of the outer planets present exciting targets for astrobiology, with Europa, Enceladus, and Titan all showing signs of environments that could support life.

Gas giants and ice giants differ fundamentally in composition. While Jupiter and Saturn are primarily hydrogen and helium, Uranus and Neptune contain significant amounts of water, ammonia, and methane ices. This distinction gives the ice giants their characteristic blue-green colors and different internal structures compared to their larger neighbors.
"""

# Section 2: Beyond Our Solar System + Space Exploration (cached at 5m TTL)
SPACE_SECTION_2 = """
Exoplanet research has revolutionized our understanding of planetary systems. The Kepler space telescope discovered thousands of planets orbiting other stars, revealing that planets are common throughout our galaxy. Some of these exoplanets reside in the habitable zone of their stars, where liquid water could exist on the surface.

The search for extraterrestrial intelligence, known as SETI, uses radio telescopes to listen for signals from advanced civilizations. While no definitive signals have been detected, the Drake Equation provides a framework for estimating the number of communicating civilizations in our galaxy.

Black holes, regions of spacetime where gravity is so strong that nothing can escape, represent some of the most extreme objects in the universe. Stellar black holes form from the collapse of massive stars, while supermassive black holes, containing millions to billions of solar masses, reside at the centers of most galaxies including our own.

The Event Horizon Telescope collaboration captured the first image of a black hole's shadow in 2019, confirming predictions from Einstein's general theory of relativity. Gravitational wave detectors have also observed the mergers of black holes and neutron stars, opening a new window on the universe.

Dark matter and dark energy together comprise about 95% of the universe's total mass-energy content. Dark matter, which does not emit or absorb light, reveals its presence through gravitational effects on visible matter. Dark energy, even more mysterious, appears to be driving the accelerated expansion of the universe.

The cosmic microwave background radiation, discovered in 1965, provides a snapshot of the universe approximately 380,000 years after the Big Bang. Detailed measurements of this radiation have confirmed the Big Bang theory and revealed information about the early universe's composition and geometry.

Modern telescopes have detected exoplanets using multiple methods including transit photometry, radial velocity measurements, and direct imaging. Transit photometry measures the slight dimming of starlight when a planet passes in front of its host star. Radial velocity detects the wobble in a star's motion caused by orbiting planets. Direct imaging captures actual light from exoplanets, though this remains challenging due to the overwhelming brightness of host stars.

Stellar evolution describes how stars change over their lifetimes. Stars form in molecular clouds when gravity causes dense regions to collapse. Nuclear fusion in the core converts hydrogen to helium, releasing enormous amounts of energy. When stars exhaust their nuclear fuel, their fate depends on their mass: smaller stars become white dwarfs, medium stars may become neutron stars, and the most massive stars explode as supernovae, potentially leaving behind black holes.

Galaxies, containing billions of stars, come in various shapes including spiral, elliptical, and irregular. The Milky Way is a barred spiral galaxy approximately 100,000 light-years in diameter. Galaxies often cluster together, forming groups and superclusters connected by cosmic filaments of dark matter and gas.

Space exploration has achieved remarkable milestones since the launch of Sputnik in 1957. Human spaceflight began with Yuri Gagarin's orbit in 1961 and culminated in the Apollo Moon landings. The International Space Station has hosted continuous human presence in space since 2000. Future missions aim to return humans to the Moon and eventually send astronauts to Mars.

Private space companies have transformed the industry, developing reusable rockets that have dramatically reduced launch costs. These advances have enabled new possibilities for satellite constellations, space tourism, and lunar exploration. Plans for permanent lunar bases and Mars colonies represent the next frontier of human expansion into space.

The study of astrobiology examines the origin, evolution, and distribution of life in the universe. Scientists search for biosignatures in planetary atmospheres and analyze extremophiles on Earth to understand the limits of life. The discovery of organic molecules on Mars and in the plumes of Enceladus fuels speculation about the possibility of life elsewhere in our solar system.

Space telescopes have revolutionized astronomy by observing wavelengths blocked by Earth's atmosphere. The Hubble Space Telescope has provided stunning images and groundbreaking discoveries for over three decades. The James Webb Space Telescope, launched in 2021, observes in infrared to study the earliest galaxies and probe planetary atmospheres for signs of life.

Understanding the universe requires collaboration across disciplines including physics, chemistry, biology, and engineering. International cooperation has enabled ambitious projects like the International Space Station and large-scale observatories. The quest to explore space continues to inspire new generations of scientists and engineers who will push the boundaries of human knowledge and capability.
"""

QUESTION_PROMPT = "Based on the context above about space, what are the two ice giant planets in our solar system and what makes them unique?"


def create_bedrock_client():
    """Create a Bedrock Runtime client with the specified profile and region."""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return session.client("bedrock-runtime")


# API-specific prefixes to ensure separate cache entries per test function
CONVERSE_STREAM_PREFIX = "[MIXED TTL - CONVERSE STREAM]\n\n"
CONVERSE_PREFIX = "[MIXED TTL - CONVERSE]\n\n"


def build_converse_content_mixed_ttl(prefix):
    """Build content for Converse API with mixed-TTL cache checkpoints.

    Uses 1h TTL on section 1 and 5m TTL on section 2.
    Longer TTL must come before shorter TTL (API constraint).
    """
    return [
        {"text": prefix + SPACE_SECTION_1},
        {"cachePoint": {"type": "default", "ttl": CACHE_TTL_LONG}},
        {"text": SPACE_SECTION_2},
        {"cachePoint": {"type": "default", "ttl": CACHE_TTL_SHORT}},
        {"text": QUESTION_PROMPT}
    ]


def test_converse_stream_mixed_ttl(client):
    """Test mixed-TTL caching with ConverseStream API."""
    print("\n" + "=" * 60)
    print("Test 1: ConverseStream (mixed TTL)")
    print("=" * 60)

    results = {"first": {}, "second": {}}

    for attempt, label in [(1, "first"), (2, "second")]:
        print(f"\nRequest {attempt} ({'cache write expected' if attempt == 1 else 'cache read expected'})...")

        content = build_converse_content_mixed_ttl(CONVERSE_STREAM_PREFIX)

        response = client.converse_stream(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
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
            "output_tokens": usage_data.get("outputTokens", 0),
            "cache_details": usage_data.get("cacheDetails", [])
        }

        print(f"  Input tokens: {results[label]['input_tokens']}")
        print(f"  Output tokens: {results[label]['output_tokens']}")
        print(f"  CacheWriteInputTokens: {results[label]['cache_write']} (total)")
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


def test_converse_mixed_ttl(client):
    """Test mixed-TTL caching with Converse API."""
    print("\n" + "=" * 60)
    print("Test 2: Converse (mixed TTL)")
    print("=" * 60)

    results = {"first": {}, "second": {}}

    for attempt, label in [(1, "first"), (2, "second")]:
        print(f"\nRequest {attempt} ({'cache write expected' if attempt == 1 else 'cache read expected'})...")

        content = build_converse_content_mixed_ttl(CONVERSE_PREFIX)

        response = client.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
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
        print(f"  CacheWriteInputTokens: {results[label]['cache_write']} (total)")
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
    """Run mixed-TTL prompt caching tests."""
    parser = argparse.ArgumentParser(
        description="Test Amazon Bedrock Prompt Caching - Mixed TTL Checkpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Demonstrates mixed-TTL cache checkpoints (1h + 5m) in a single request.
Shows per-TTL token breakdown via the cacheDetails response field.

Only tests Converse and ConverseStream APIs because InvokeModel does not
return cacheDetails in its response.

Examples:
  python test_mixed_ttl_caching.py
        """
    )
    parser.parse_args()

    print("=" * 60)
    print("Testing Mixed-TTL Prompt Caching with Amazon Bedrock")
    print("=" * 60)
    print(f"Model: {MODEL_ID}")
    print(f"Region: {AWS_REGION}")
    print(f"Profile: {AWS_PROFILE}")
    print(f"Cache TTLs: {CACHE_TTL_LONG} (section 1), {CACHE_TTL_SHORT} (section 2)")
    print(f"APIs tested: ConverseStream, Converse")

    client = create_bedrock_client()

    results = {}

    results["ConverseStream"] = test_converse_stream_mixed_ttl(client)
    results["Converse"] = test_converse_mixed_ttl(client)

    print("\n" + "=" * 60)
    print("SUMMARY (mixed-TTL caching)")
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
