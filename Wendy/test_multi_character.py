"""
Comprehensive test suite for the Multi-Character System.

Run standalone: python test_multi_character.py
No pytest required. No LLM API key required. No Flask server required.
"""

import sys
import os
import json
import sqlite3
import re
from pathlib import Path

# Ensure we can import from the Wendy directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import character_engine
import database


# ============================================================================
# Test infrastructure
# ============================================================================

class TestResults:
    """Track test results and print summary."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def add_pass(self, name, detail=""):
        self.passed += 1
        msg = f"[PASS] {name}"
        if detail:
            msg += f": {detail}"
        self.results.append(msg)
        print(msg)

    def add_fail(self, name, reason):
        self.failed += 1
        msg = f"[FAIL] {name}: {reason}"
        self.results.append(msg)
        print(msg)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n=== Results: {self.passed}/{total} passed, {self.failed} failed ===")
        return self.failed == 0


results = TestResults()

# Paths
WENDY_DIR = Path(__file__).parent
CHARACTERS_DIR = WENDY_DIR / "characters"
TEMPLATES_DIR = WENDY_DIR / "templates"
SITE_DIR = WENDY_DIR.parent / "gamemodes-site" / "Wendy"


# ============================================================================
# Test 1: Character JSON Loading
# ============================================================================

def test_character_json_loading():
    """All character files load without errors, have required fields."""
    required_fields = ["id", "name", "game", "role", "system_prompt_base", "stages"]
    char_files = sorted(CHARACTERS_DIR.glob("*.json"))
    # Filter out README.json if it exists
    char_files = [f for f in char_files if f.name != "README.md" and f.suffix == ".json"]

    loaded = 0
    errors = []

    for char_file in char_files:
        try:
            with open(char_file, encoding="utf-8") as f:
                char = json.load(f)

            missing = [field for field in required_fields if field not in char]
            if missing:
                errors.append(f"{char_file.name}: missing fields {missing}")
            else:
                loaded += 1
        except json.JSONDecodeError as e:
            errors.append(f"{char_file.name}: JSON parse error: {e}")
        except Exception as e:
            errors.append(f"{char_file.name}: {e}")

    total = len(char_files)
    if errors:
        results.add_fail("Character JSON loading", f"{loaded}/{total} loaded. Errors: {'; '.join(errors)}")
    else:
        results.add_pass("Character JSON loading", f"{loaded}/{total}")


# ============================================================================
# Test 2: Character Engine Functions
# ============================================================================

def test_character_engine_functions():
    """All engine functions work without errors."""
    errors = []
    char_files = sorted(CHARACTERS_DIR.glob("*.json"))
    char_ids = []
    for f in char_files:
        if f.suffix == ".json" and f.name != "README.md":
            with open(f, encoding="utf-8") as fh:
                char = json.load(fh)
                char_ids.append(char.get("id", f.stem))

    if not char_ids:
        results.add_fail("Character engine functions", "No character files found")
        return

    test_id = char_ids[0]

    # Test load_character()
    try:
        char = character_engine.load_character(test_id)
        assert isinstance(char, dict)
    except Exception as e:
        errors.append(f"load_character(): {e}")

    # Test get_available_characters()
    try:
        chars = character_engine.get_available_characters()
        assert isinstance(chars, list)
        assert len(chars) > 0
    except Exception as e:
        errors.append(f"get_available_characters(): {e}")

    # Test build_system_prompt()
    try:
        prompt = character_engine.build_system_prompt(test_id, affinity=50)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
    except Exception as e:
        errors.append(f"build_system_prompt(): {e}")

    # Test get_stage()
    try:
        char = character_engine.load_character(test_id)
        stage = character_engine.get_stage(char, 50)
        assert isinstance(stage, str)
        assert stage in char["stages"]
    except Exception as e:
        errors.append(f"get_stage(): {e}")

    # Test calculate_affinity_shift()
    try:
        new_aff = character_engine.calculate_affinity_shift(test_id, "thank you", 50)
        assert isinstance(new_aff, (int, float))
        assert 0 <= new_aff <= 100
    except Exception as e:
        errors.append(f"calculate_affinity_shift(): {e}")

    # Test should_end_conversation()
    try:
        end = character_engine.should_end_conversation(test_id, 50, 10)
        assert isinstance(end, bool)
    except Exception as e:
        errors.append(f"should_end_conversation(): {e}")

    # Test format_messages_for_llm()
    try:
        messages = character_engine.format_messages_for_llm(
            test_id,
            [{"role": "user", "content": "Hello"}],
            affinity=50
        )
        assert isinstance(messages, list)
        assert len(messages) >= 2  # system + user
        assert messages[0]["role"] == "system"
    except Exception as e:
        errors.append(f"format_messages_for_llm(): {e}")

    if errors:
        results.add_fail("Character engine functions", "; ".join(errors))
    else:
        results.add_pass("Character engine functions")


# ============================================================================
# Test 3: System Prompt Building
# ============================================================================

def test_system_prompt_building():
    """Each character produces a non-empty system prompt with stage behavior injected."""
    char_files = sorted(CHARACTERS_DIR.glob("*.json"))
    errors = []

    for char_file in char_files:
        if char_file.suffix != ".json" or char_file.name == "README.md":
            continue
        with open(char_file, encoding="utf-8") as f:
            char = json.load(f)
        char_id = char.get("id", char_file.stem)

        try:
            prompt = character_engine.build_system_prompt(char_id, affinity=50)
            if not prompt or len(prompt) < 50:
                errors.append(f"{char_id}: prompt too short ({len(prompt)} chars)")
                continue

            # Check that stage behavior is injected
            stage = character_engine.get_stage(char, 50)
            stage_behavior = char["stages"][stage]["behavior"]
            if stage_behavior not in prompt:
                errors.append(f"{char_id}: stage behavior not found in prompt at affinity 50")
        except Exception as e:
            errors.append(f"{char_id}: {e}")

    if errors:
        results.add_fail("System prompt building", "; ".join(errors))
    else:
        total = len([f for f in char_files if f.suffix == ".json" and f.name != "README.md"])
        results.add_pass("System prompt building", f"{total}/{total}")


# ============================================================================
# Test 4: Affinity Stage Resolution
# ============================================================================

def test_affinity_stage_resolution():
    """Each character's stages resolve correctly at different affinity values."""
    char_files = sorted(CHARACTERS_DIR.glob("*.json"))
    test_affinities = [0, 25, 50, 75, 100]
    errors = []

    for char_file in char_files:
        if char_file.suffix != ".json" or char_file.name == "README.md":
            continue
        with open(char_file, encoding="utf-8") as f:
            char = json.load(f)
        char_id = char.get("id", char_file.stem)

        for aff in test_affinities:
            try:
                stage = character_engine.get_stage(char, aff)
                if stage not in char["stages"]:
                    errors.append(f"{char_id}: stage '{stage}' not in stages at affinity {aff}")
            except Exception as e:
                errors.append(f"{char_id}: error at affinity {aff}: {e}")

    if errors:
        results.add_fail("Affinity stage resolution", "; ".join(errors))
    else:
        results.add_pass("Affinity stage resolution")


# ============================================================================
# Test 5: Affinity Shift Calculation
# ============================================================================

def test_affinity_shift_calculation():
    """Positive and negative keywords produce correct shift directions."""
    char_files = sorted(CHARACTERS_DIR.glob("*.json"))
    errors = []

    for char_file in char_files:
        if char_file.suffix != ".json" or char_file.name == "README.md":
            continue
        with open(char_file, encoding="utf-8") as f:
            char = json.load(f)
        char_id = char.get("id", char_file.stem)
        shifts = char.get("affinity_shifts", {})
        positives = shifts.get("positive", [])
        negatives = shifts.get("negative", [])

        if positives:
            # Test a positive keyword
            keyword = positives[0]
            new_aff = character_engine.calculate_affinity_shift(char_id, keyword, 50)
            if new_aff <= 50:
                errors.append(f"{char_id}: positive keyword '{keyword}' did not increase affinity (got {new_aff})")

        if negatives:
            # Test a negative keyword
            keyword = negatives[0]
            new_aff = character_engine.calculate_affinity_shift(char_id, keyword, 50)
            if new_aff >= 50:
                errors.append(f"{char_id}: negative keyword '{keyword}' did not decrease affinity (got {new_aff})")

    if errors:
        results.add_fail("Affinity shift calculation", "; ".join(errors))
    else:
        results.add_pass("Affinity shift calculation")


# ============================================================================
# Test 6: Database Schema
# ============================================================================

def test_database_schema():
    """character_id column exists in conversations table."""
    # Use a temporary database
    tmp_db = WENDY_DIR / "test_temp.db"
    original_db_path = database._db_path
    try:
        if tmp_db.exists():
            tmp_db.unlink()

        # Override the module-level db path
        database._db_path = str(tmp_db)
        database.init_db(str(tmp_db))

        # Check that character_id column exists
        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        if "character_id" not in columns:
            results.add_fail("Database schema", "character_id column missing from conversations table")
        else:
            results.add_pass("Database schema", "character_id column exists")
    except Exception as e:
        results.add_fail("Database schema", str(e))
    finally:
        # Restore original db path
        try:
            database._db_path = original_db_path
        except:
            pass
        if tmp_db.exists():
            try:
                tmp_db.unlink()
            except:
                pass


# ============================================================================
# Test 7: API Routes Exist
# ============================================================================

def test_api_routes_exist():
    """Character routes are registered in the Flask app."""
    app_py = WENDY_DIR / "app.py"
    content = app_py.read_text(encoding="utf-8")

    required_routes = [
        '"/api/characters"',
        '"/api/characters/<character_id>/chat"',
        '"/api/characters/<character_id>/conversations"',
        '"/api/characters/<character_id>/new"',
        '"/characters"',
        '"/chat/<character_id>"',
    ]

    missing = [route for route in required_routes if route not in content]

    if missing:
        results.add_fail("API routes exist", f"Missing routes: {missing}")
    else:
        results.add_pass("API routes exist", f"{len(required_routes)} routes found")


# ============================================================================
# Test 8: Templates Exist
# ============================================================================

def test_templates_exist():
    """characters.html and character_chat.html exist."""
    chars_tpl = TEMPLATES_DIR / "characters.html"
    chat_tpl = TEMPLATES_DIR / "character_chat.html"

    missing = []
    if not chars_tpl.exists():
        missing.append("characters.html")
    if not chat_tpl.exists():
        missing.append("character_chat.html")

    if missing:
        results.add_fail("Templates exist", f"Missing: {missing}")
    else:
        results.add_pass("Templates exist", "characters.html, character_chat.html")


# ============================================================================
# Test 9: No IFS References
# ============================================================================

def test_no_ifs_references():
    """Scan all character JSON files and templates for IFS terms."""
    ifs_terms = ["IFS", "Internal Family Systems", "Manager", "Firefighter", "Exile"]
    # We need to be careful: "Manager" and "Exile" can appear in normal context.
    # We'll look for them in combination or as standalone IFS references.
    # The safest approach: flag any occurrence of "IFS" or "Internal Family Systems".
    # For "Manager", "Firefighter", "Exile" — only flag if they appear in personality_layers
    # or in a context suggesting IFS terminology.

    strict_terms = ["IFS", "Internal Family Systems"]
    contextual_terms = ["Manager", "Firefighter", "Exile"]

    violations = []

    # Check character JSON files
    for char_file in CHARACTERS_DIR.glob("*.json"):
        content = char_file.read_text(encoding="utf-8")
        for term in strict_terms:
            if term.lower() in content.lower():
                violations.append(f"{char_file.name}: contains '{term}'")

    # Check templates
    for tpl_file in TEMPLATES_DIR.glob("*.html"):
        content = tpl_file.read_text(encoding="utf-8")
        for term in strict_terms:
            if term.lower() in content.lower():
                violations.append(f"{tpl_file.name}: contains '{term}'")

    # Check character_engine.py
    engine_file = WENDY_DIR / "character_engine.py"
    engine_content = engine_file.read_text(encoding="utf-8")
    for term in strict_terms:
        if term.lower() in engine_content.lower():
            violations.append(f"character_engine.py: contains '{term}'")

    if violations:
        results.add_fail("No IFS references", "; ".join(violations))
    else:
        results.add_pass("No IFS references", "Clean across all character files and templates")


# ============================================================================
# Test 10: Character IDs Match Filenames
# ============================================================================

def test_character_ids_match_filenames():
    """Each JSON's id field matches its filename (minus .json)."""
    mismatches = []

    for char_file in CHARACTERS_DIR.glob("*.json"):
        if char_file.suffix != ".json" or char_file.name == "README.md":
            continue
        try:
            with open(char_file, encoding="utf-8") as f:
                char = json.load(f)
            expected_id = char_file.stem
            actual_id = char.get("id", "")
            if actual_id != expected_id:
                mismatches.append(f"{char_file.name}: id='{actual_id}' expected='{expected_id}'")
        except Exception as e:
            mismatches.append(f"{char_file.name}: {e}")

    if mismatches:
        results.add_fail("Character IDs match filenames", "; ".join(mismatches))
    else:
        results.add_pass("Character IDs match filenames", f"{len(list(CHARACTERS_DIR.glob('*.json')))} files checked")


# ============================================================================
# Bonus: Verify game field consistency
# ============================================================================

def test_game_field_consistency():
    """Verify character IDs follow {game}_{character} convention and game field matches."""
    issues = []

    for char_file in CHARACTERS_DIR.glob("*.json"):
        if char_file.suffix != ".json" or char_file.name == "README.md":
            continue
        try:
            with open(char_file, encoding="utf-8") as f:
                char = json.load(f)
            char_id = char.get("id", "")
            game = char.get("game", "")

            # Wendy is an exception — original character
            if char_id == "wendy":
                if game != "Original":
                    issues.append(f"{char_id}: game='{game}' expected='Original'")
                continue

            # For others, check {game}_{character} pattern
            if "_" in char_id:
                game_prefix = char_id.split("_")[0]
                # Map prefix to expected game name
                game_map = {
                    "skyrim": "Skyrim",
                    "fallout4": "Fallout 4",
                }
                expected_game = game_map.get(game_prefix, None)
                if expected_game and game != expected_game:
                    issues.append(f"{char_id}: game='{game}' expected='{expected_game}'")
            else:
                # Non-wendy characters without underscore — just warn
                pass
        except Exception as e:
            issues.append(f"{char_file.name}: {e}")

    if issues:
        results.add_fail("Game field consistency", "; ".join(issues))
    else:
        results.add_pass("Game field consistency")


# ============================================================================
# Main
# ============================================================================

def main():
    print("=== Multi-Character System Tests ===\n")

    test_character_json_loading()
    test_character_engine_functions()
    test_system_prompt_building()
    test_affinity_stage_resolution()
    test_affinity_shift_calculation()
    test_database_schema()
    test_api_routes_exist()
    test_templates_exist()
    test_no_ifs_references()
    test_character_ids_match_filenames()
    test_game_field_consistency()

    print()
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
