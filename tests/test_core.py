import random
import tempfile
import unittest
from pathlib import Path

from wubi98type.config import Config, load_config, save_config
from wubi98type.data import (
    FIRST_LEVEL_CHARS,
    KEY_NAME_CHARS,
    Dictionary,
    Entry,
    canonical_code,
    is_hanzi,
    parse_table,
)
from wubi98type.drill import PressResult, Session
from wubi98type.encoding import WordIndex
from wubi98type.keymap import KEYMAP, MNEMONICS
from wubi98type.keytable import KEY_BOXES, TABLE_SIZE, KeyTableImages, find_table_image
from wubi98type.lookup import ReverseLookup, clean_code
from wubi98type.passage import build_passage, read_text_file
from wubi98type.poems import POEMS, POEM_BY_ID

ROOT = Path(__file__).resolve().parents[1]


class DataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dictionary = Dictionary.load(ROOT)

    def test_first_level_scope_has_25_chars(self) -> None:
        entries = self.dictionary.char_scope("first")
        self.assertEqual(len(entries), 25)
        self.assertEqual({e.text for e in entries}, set(FIRST_LEVEL_CHARS))
        self.assertTrue(all(e.code for e in entries))

    def test_keyname_scope_has_24_chars(self) -> None:
        entries = self.dictionary.char_scope("keyname")
        self.assertEqual(len(entries), 24)
        self.assertEqual({e.text for e in entries}, set(KEY_NAME_CHARS))

    def test_scopes_are_not_empty(self) -> None:
        for scope in ("level2", "level3", "full", "all"):
            self.assertGreater(len(self.dictionary.char_scope(scope)), 0, scope)
        for scope in ("two", "three", "four"):
            self.assertGreater(len(self.dictionary.phrase_scope(scope)), 0, scope)

    def test_full_codes_have_expected_length(self) -> None:
        for entry in self.dictionary.char_scope("level2")[:100]:
            self.assertIn(len(entry.code), (2, 3, 4))
            self.assertLessEqual(entry.min_code_len, len(entry.code))

    def test_canonical_code_prefers_longest(self) -> None:
        self.assertEqual(canonical_code(["a", "aaa", "aaaa"]), "aaaa")
        self.assertEqual(canonical_code(["aad", "aadk"]), "aadk")

    def test_entries_keep_all_code_variants(self) -> None:
        entry = self.dictionary._char_index["的"]
        self.assertEqual(entry.code, "rqyy")
        self.assertIn("r", entry.codes)
        self.assertIn("rqyy", entry.codes)
        self.assertEqual(entry.min_code_len, 1)
        self.assertEqual(entry.short_codes, ("r", "rqy"))

    def test_parse_table_ignores_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.txt"
            path.write_text(
                "KeyCode=abc\n[Data]\naaaa 工\naauh 藏\nbad word\n",
                encoding="utf-8",
            )
            table = parse_table(path)
        self.assertEqual(table["工"], ["aaaa"])
        self.assertEqual(table["藏"], ["aauh"])
        self.assertNotIn("bad", table)

    def test_mixed_buckets_include_chars_and_phrases(self) -> None:
        buckets = self.dictionary.buckets("mixed", "first", "two")
        self.assertEqual(len(buckets), 2)
        self.assertEqual(buckets[0][0], self.dictionary.char_scope("first"))
        self.assertTrue(all(len(e.text) <= 4 for e in buckets[1][0]))


class KeymapTest(unittest.TestCase):
    def test_mnemonics_cover_every_key(self) -> None:
        self.assertEqual(set(MNEMONICS), set(KEYMAP))
        self.assertEqual(len(MNEMONICS), 25)

    def test_mnemonics_are_seven_characters(self) -> None:
        for letter, line in MNEMONICS.items():
            self.assertEqual(len(line), 7, f"{letter}: {line}")


class KeyTableTest(unittest.TestCase):
    def test_boxes_cover_all_keys(self) -> None:
        self.assertEqual(set(KEY_BOXES), set(KEYMAP))

    def test_boxes_are_inside_image(self) -> None:
        width, height = TABLE_SIZE
        for letter, (x, y, box_w, box_h) in KEY_BOXES.items():
            self.assertGreater(box_w, 0, letter)
            self.assertGreater(box_h, 0, letter)
            self.assertGreaterEqual(x, 0, letter)
            self.assertGreaterEqual(y, 0, letter)
            self.assertLessEqual(x + box_w, width, letter)
            self.assertLessEqual(y + box_h, height, letter)

    def test_boxes_do_not_overlap(self) -> None:
        items = list(KEY_BOXES.items())
        for index, (letter, box) in enumerate(items):
            ax, ay, aw, ah = box
            for other_letter, other in items[index + 1 :]:
                bx, by, bw, bh = other
                overlap = (
                    ax < bx + bw
                    and bx < ax + aw
                    and ay < by + bh
                    and by < ay + ah
                )
                self.assertFalse(overlap, f"{letter} 与 {other_letter}")

    def test_crop_from_real_image(self) -> None:
        path = find_table_image()
        if path is None:
            self.skipTest("未找到 wubi98-table.png")
        images = KeyTableImages(path)
        for letter, (x, y, width, height) in KEY_BOXES.items():
            texture = images.texture(letter)
            self.assertIsNotNone(texture, letter)
            self.assertEqual(texture.get_width(), width, letter)
            self.assertEqual(texture.get_height(), height, letter)
        preview = images.texture("e", (132, 162))
        self.assertIsNotNone(preview)
        self.assertEqual((preview.get_width(), preview.get_height()), (132, 162))


class LookupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lookup = ReverseLookup.load(ROOT)

    def test_exact_short_code(self) -> None:
        result = self.lookup.search("a")
        texts = {item.text for item in result.exact}
        self.assertIn("工", texts)
        self.assertIn("戈", texts)

    def test_exact_full_code(self) -> None:
        result = self.lookup.search("trng")
        self.assertTrue(
            any(item.text == "鹅" and item.code == "trng" for item in result.exact)
        )

    def test_phrase_lookup(self) -> None:
        result = self.lookup.search("xciy")
        self.assertTrue(any(item.text == "经济" for item in result.exact))

    def test_prefix_lookup(self) -> None:
        result = self.lookup.search("trng")
        self.assertTrue(
            all(item.code.startswith("trng") for item in result.prefix)
        )
        broader = self.lookup.search("tr")
        self.assertGreater(broader.prefix_total, 0)
        self.assertTrue(all(item.code.startswith("tr") for item in broader.prefix))

    def test_include_phrase_filter(self) -> None:
        without = self.lookup.search("aaaa", include_phrases=False)
        self.assertTrue(all(len(item.text) == 1 for item in without.exact))
        with_phrases = self.lookup.search("aaaa", include_phrases=True)
        self.assertTrue(any(len(item.text) > 1 for item in with_phrases.exact))

    def test_limit_and_truncation(self) -> None:
        result = self.lookup.search("a", limit=5)
        self.assertLessEqual(len(result.prefix), 5)
        self.assertGreater(result.prefix_total, 5)
        self.assertTrue(result.truncated)

    def test_clean_code(self) -> None:
        self.assertEqual(clean_code("TRNG"), "trng")
        self.assertEqual(clean_code("tr9ng!"), "trng")
        self.assertEqual(clean_code("abcdefg"), "abcd")
        self.assertEqual(clean_code("zzz"), "")

    def test_empty_query(self) -> None:
        result = self.lookup.search("")
        self.assertEqual(result.total, 0)
        self.assertEqual(result.exact, ())
        self.assertEqual(result.prefix, ())


class EncodingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = WordIndex.load(ROOT)

    def test_char_preferred_short_code(self) -> None:
        word = self.index.get("的")
        self.assertIsNotNone(word)
        self.assertEqual(word.preferred_code, "r")
        self.assertEqual(word.full_code, "rqyy")
        self.assertTrue(word.has_short_code)

    def test_phrase_entry(self) -> None:
        word = self.index.get("计算机")
        self.assertIsNotNone(word)
        self.assertEqual(word.kind, "phrase")
        self.assertEqual(word.preferred_code, "ytsw")

    def test_longest_phrase_first(self) -> None:
        result = self.index.encode("计算机")
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].text, "计算机")
        self.assertEqual(result.minimal_code, "ytsw")

    def test_sentence_segmentation(self) -> None:
        result = self.index.encode("我爱北京天安门")
        self.assertEqual(
            "".join(segment.text for segment in result.segments),
            "我爱北京天安门",
        )
        self.assertTrue(any(len(segment.text) > 1 for segment in result.segments))
        self.assertEqual(result.missing, ())
        self.assertEqual(len(result.minimal_code), sum(
            len(segment.code) for segment in result.segments
        ))

    def test_punctuation_ignored(self) -> None:
        result = self.index.encode("中国，加油！")
        self.assertEqual(
            "".join(segment.text for segment in result.segments),
            "中国加油",
        )
        self.assertEqual(result.missing, ())

    def test_minimal_and_full_codes(self) -> None:
        result = self.index.encode("的")
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.minimal_code, "r")
        self.assertEqual(result.full_code, "rqyy")
        self.assertTrue(result.has_short_codes)

    def test_spaced_codes_for_sentence(self) -> None:
        result = self.index.encode("我爱北京天安门")
        self.assertEqual(
            result.minimal_code_spaced,
            " ".join(segment.code for segment in result.segments),
        )
        self.assertIn(" ", result.minimal_code_spaced)
        self.assertEqual(
            result.full_code_spaced,
            " ".join(segment.full_code for segment in result.segments),
        )

    def test_codes_sorted_shortest_first(self) -> None:
        word = self.index.get("工")
        self.assertIsNotNone(word)
        lengths = [len(code) for code in word.codes]
        self.assertEqual(lengths, sorted(lengths))
        self.assertEqual(word.preferred_code, "a")
        self.assertEqual(word.full_code, "aaaa")


class PoemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.words = WordIndex.load(ROOT)

    def test_poem_collection(self) -> None:
        self.assertEqual(len(POEMS), 80)
        self.assertEqual(len(POEM_BY_ID), 80)
        self.assertEqual([poem.number for poem in POEMS], list(range(1, 81)))
        for poem in POEMS:
            self.assertTrue(poem.title)
            self.assertTrue(poem.author)
            self.assertTrue(poem.lines)
            self.assertTrue(poem.text)

    def test_all_poem_characters_have_codes(self) -> None:
        for poem in POEMS:
            passage = build_passage(poem.text, poem.title, self.words)
            hanzi_count = sum(1 for char in poem.text if is_hanzi(char))
            self.assertEqual(passage.char_count, hanzi_count, poem.title)
            for position, item in zip(passage.positions, passage.items):
                self.assertEqual(
                    poem.text[position : position + len(item.text)],
                    item.text,
                    poem.title,
                )

    def test_duplicate_titles_are_disambiguated(self) -> None:
        labels = [poem.label for poem in POEMS]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertIn("绝句", "".join(labels))
        self.assertTrue(any("悯农（其一）" in label for label in labels))
        self.assertTrue(any("悯农（其二）" in label for label in labels))

    def test_build_passage_skips_punctuation(self) -> None:
        text = "床前明月光，\n疑是地上霜。"
        passage = build_passage(text, "静夜思", self.words)
        self.assertEqual(passage.char_count, 10)
        self.assertEqual(
            "".join(item.text for item in passage.items),
            "床前明月光疑是地上霜",
        )
        for position, item in zip(passage.positions, passage.items):
            self.assertEqual(
                passage.text[position : position + len(item.text)],
                item.text,
            )

    def test_sequence_session_keeps_order(self) -> None:
        items = [Entry("床", "ysi"), Entry("前", "uej")]
        session = Session.sequence(items)
        self.assertEqual(session.total, 2)
        self.assertEqual(session.current.text, "床")
        for letter in session.current.code:
            result = session.press(letter)
        self.assertIs(result, PressResult.ITEM_DONE)
        self.assertEqual(session.current.text, "前")

    def test_passage_uses_phrases_and_short_codes(self) -> None:
        passage = build_passage("我爱北京天安门。", "测试", self.words)
        self.assertEqual(
            [(item.text, item.code) for item in passage.items],
            [("我", "q"), ("爱", "ep"), ("北京", "uxyi"), ("天安门", "gpuy")],
        )
        self.assertEqual(passage.char_count, 7)
        self.assertEqual(passage.segment_count, 4)

    def test_read_text_file_encodings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            utf8 = Path(tmp) / "utf8.txt"
            utf8.write_text("床前明月光\r\n疑是地上霜", encoding="utf-8")
            self.assertEqual(read_text_file(utf8), "床前明月光\n疑是地上霜")
            gbk = Path(tmp) / "gbk.txt"
            gbk.write_bytes("床前明月光".encode("gb18030"))
            self.assertEqual(read_text_file(gbk), "床前明月光")
            utf16 = Path(tmp) / "utf16.txt"
            utf16.write_bytes("床前明月光".encode("utf-16"))
            self.assertEqual(read_text_file(utf16), "床前明月光")

    def test_build_empty_passage_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_passage("，。！", "空文稿", self.words)


class SessionTest(unittest.TestCase):
    def test_wrong_key_does_not_advance(self) -> None:
        session = Session([([Entry("工", "aaaa")], 1.0)], 1)
        self.assertIs(session.press("g"), PressResult.WRONG)
        self.assertEqual(session.errors, 1)
        self.assertEqual(session.typed, [])
        self.assertEqual(session.expected, "a")

    def test_complete_item_and_session(self) -> None:
        session = Session([([Entry("工", "aaaa")], 1.0)], 1)
        for letter in "aaaa":
            result = session.press(letter)
        self.assertIs(result, PressResult.SESSION_DONE)
        self.assertTrue(session.is_finished)
        self.assertEqual(session.chars_completed, 1)
        self.assertEqual(session.accuracy, 100.0)
        self.assertEqual(session.mistakes, [])

    def test_backspace(self) -> None:
        session = Session([([Entry("工", "aaaa")], 1.0)], 1)
        session.press("a")
        session.press("a")
        self.assertEqual(session.typed, ["a", "a"])
        self.assertTrue(session.backspace())
        self.assertEqual(session.typed, ["a"])
        self.assertEqual(session.expected, "a")
        self.assertTrue(session.backspace())
        self.assertFalse(session.backspace())

    def test_skip_records_mistake(self) -> None:
        session = Session(
            [([Entry("工", "aaaa"), Entry("戈", "agny")], 1.0)],
            2,
            rng=random.Random(0),
        )
        skipped = session.current.text
        result = session.skip()
        self.assertIs(result, PressResult.ITEM_DONE)
        self.assertEqual(len(session.mistakes), 1)
        self.assertTrue(session.mistakes[0].skipped)
        self.assertEqual(session.mistakes[0].text, skipped)
        self.assertEqual(session.chars_completed, 0)

    def test_mistakes_and_retry_items(self) -> None:
        session = Session([([Entry("工", "aaaa")], 1.0)], 1)
        session.press("x")  # 错一次
        for letter in "aaaa":
            session.press(letter)
        self.assertEqual(len(session.mistakes), 1)
        self.assertEqual(session.mistakes[0].errors, 1)
        retry = session.retry_items()
        self.assertEqual([e.text for e in retry], ["工"])

    def test_speed_uses_elapsed_time(self) -> None:
        clock = [100.0]
        session = Session(
            [([Entry("工", "aaaa")], 1.0)],
            1,
            now=lambda: clock[0],
        )
        session.press("a")
        clock[0] = 130.0
        for letter in "aaa":
            session.press(letter)
        self.assertAlmostEqual(session.elapsed, 30.0)
        self.assertAlmostEqual(session.speed, 2.0)

    def test_pause_excludes_lookup_time(self) -> None:
        clock = [100.0]
        session = Session(
            [([Entry("工", "aaaa")], 1.0)],
            1,
            now=lambda: clock[0],
        )
        session.press("a")
        clock[0] = 110.0
        session.pause()
        self.assertTrue(session.is_paused)
        clock[0] = 150.0
        self.assertAlmostEqual(session.elapsed, 10.0)
        session.resume()
        self.assertFalse(session.is_paused)
        clock[0] = 160.0
        self.assertAlmostEqual(session.elapsed, 20.0)

    def test_space_commits_short_code(self) -> None:
        entry = Entry("的", "rqyy", 1, ("r", "rqyy"))
        session = Session([([entry], 1.0)], 1)
        self.assertIs(session.press("r"), PressResult.CORRECT)
        self.assertTrue(session.can_commit_short())
        self.assertIs(session.commit_short(), PressResult.SESSION_DONE)
        self.assertTrue(session.is_finished)
        self.assertEqual(session.chars_completed, 1)
        self.assertEqual(session.keystrokes, 1)
        self.assertEqual(session.accuracy, 100.0)

    def test_space_needs_a_complete_valid_short_code(self) -> None:
        entry = Entry("的", "rqyy", 1, ("r", "rqyy"))
        session = Session([([entry], 1.0)], 1)
        self.assertIs(session.commit_short(), PressResult.IGNORED)
        session.press("r")
        session.press("q")
        self.assertFalse(session.can_commit_short())
        self.assertIs(session.commit_short(), PressResult.IGNORED)
        self.assertFalse(session.is_finished)
        self.assertEqual(session.typed, ["r", "q"])

    def test_space_retry_keeps_short_codes(self) -> None:
        entry = Entry("的", "rqyy", 1, ("r", "rqyy"))
        session = Session([([entry], 1.0)], 1)
        session.press("x")
        session.press("r")
        self.assertIs(session.commit_short(), PressResult.SESSION_DONE)
        self.assertEqual(len(session.mistakes), 1)
        retry = session.retry_items()
        self.assertIn("r", retry[0].codes)

    def test_empty_bucket_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Session([([], 1.0)], 10)

    def test_accuracy_accounts_for_errors(self) -> None:
        session = Session([([Entry("工", "aaaa")], 1.0)], 1)
        session.press("a")
        session.press("x")
        session.press("a")
        self.assertAlmostEqual(session.accuracy, 200 / 3)


class ConfigTest(unittest.TestCase):
    def test_roundtrip_and_normalise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = Config(mode="phrase", char_scope="nope", count=9999)
            config.normalise()
            save_config(config, path)
            loaded = load_config(path)
        self.assertEqual(loaded.mode, "phrase")
        self.assertEqual(loaded.char_scope, "level2")
        self.assertEqual(loaded.count, 500)

    def test_record_requires_accuracy(self) -> None:
        config = Config()
        self.assertFalse(
            config.record("char", speed=100, accuracy=50, chars=20)
        )
        self.assertTrue(
            config.record("char", speed=80, accuracy=98, chars=20)
        )
        self.assertFalse(
            config.record("char", speed=70, accuracy=99, chars=20)
        )
        self.assertTrue(
            config.record("char", speed=90, accuracy=97, chars=20)
        )

    def test_text_scope_normalised(self) -> None:
        config = Config(text_scope="bogus").normalise()
        self.assertEqual(config.text_scope, "poem-01")
        config = Config(text_scope="custom", text_path=123).normalise()
        self.assertEqual(config.text_scope, "custom")
        self.assertEqual(config.text_path, "")


if __name__ == "__main__":
    unittest.main()
