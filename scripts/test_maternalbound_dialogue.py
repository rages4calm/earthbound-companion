"""Converter safety checks using synthetic bytecode, without game content."""
import tempfile
from pathlib import Path
import unittest

from maternalbound_dialogue import ConversionError, relocate_bytes, source_labels

SPECS = {
    (0x02,): ("end", ()),
    (0x08,): ("call", ("LABEL",)),
    (0x19, 0x02): ("menu", ("STRING",)),
    (0x1F, 0xC0): ("switch_call", ("JUMP_TABLE",)),
    (0x1A, 0x18): ("redux_try_give_money", ("U32",)),
    (0x1A, 0x0C): ("redux_native_routine", ("U24", "U8")),
}


class DialogueConversionTests(unittest.TestCase):
    def test_compressed_expansion_preserves_instruction_boundaries(self):
        decoded = relocate_bytes(bytes.fromhex("20 15 00 08 00 00 F3 00 02"), SPECS, [b"abcd"])
        self.assertEqual(decoded.data, bytes.fromhex("20 61 62 63 64 08 00 00 F3 00 02"))
        self.assertEqual(decoded.boundaries[3], 5)
        self.assertEqual(decoded.pointers, [(6, 0xF30000, "call")])

    def test_compressed_index_requires_dictionary_entry(self):
        with self.assertRaises(ConversionError):
            relocate_bytes(bytes.fromhex("16 00"), SPECS, [b"a"])

    def test_jump_table_decodes_exact_count(self):
        decoded = relocate_bytes(bytes.fromhex("1F C0 02 00 00 F3 00 04 00 F3 00 02"), SPECS, [])
        self.assertEqual(decoded.pointers, [(3, 0xF30000, "switch_call"), (7, 0xF30004, "switch_call")])

    def test_missing_switch_entry_fails_without_silent_repair(self):
        with self.assertRaises(ConversionError):
            relocate_bytes(bytes.fromhex("1F C0 02 00 00 F3 00 02"), SPECS, [])

    def test_callback_after_dual_column_string_is_a_pointer(self):
        script = bytes.fromhex("19 02 61 62 03 63 64 00 34 12 F3 00 02")
        decoded = relocate_bytes(script, SPECS, [])
        self.assertEqual(decoded.data, script)
        self.assertEqual(decoded.pointers, [(8, 0xF31234, "menu")])

    def test_dual_column_without_callback(self):
        script = bytes.fromhex("19 02 61 04 62 00 02")
        self.assertEqual(relocate_bytes(script, SPECS, []).pointers, [])

    def test_truncated_dual_column_fails(self):
        with self.assertRaises(ConversionError):
            relocate_bytes(bytes.fromhex("19 02 61 04 62"), SPECS, [])

    def test_money_operand_is_never_decoded_as_script(self):
        script = bytes.fromhex("1A 18 08 15 02 FF 02")
        decoded = relocate_bytes(script, SPECS, [])
        self.assertEqual(decoded.data, script)
        self.assertEqual(decoded.opcodes, {"redux_try_give_money": 1, "end": 1})

    def test_native_call_is_catalogued_without_executing_code(self):
        decoded = relocate_bytes(bytes.fromhex("1A 0C 12 34 FC 81 02"), SPECS, [])
        self.assertEqual(decoded.routines, [(0xFC3412, 0x81)])

    def test_unknown_command_fails_closed(self):
        with self.assertRaises(ConversionError):
            relocate_bytes(bytes.fromhex("1A FF 02"), SPECS, [])

    def test_source_classification_excludes_assembly_and_patch_directives(self):
        source = 'first: {\nnext:\nLDA_i(1)\n}\ntext: {\n"Hi" eob\n}\npatch:\nROMTBL[0] = {}\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"sample.ccs"
            path.write_text(source)
            kinds = source_labels(path)
        self.assertEqual(kinds["first"], "assembly")
        self.assertEqual(kinds["next"], "assembly")
        self.assertEqual(kinds["text"], "script")
        self.assertEqual(kinds["patch"], "raw-data")


if __name__ == "__main__":
    unittest.main()
