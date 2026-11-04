from types import SimpleNamespace
import bz2
import pytest
from multigenomic_extractor.domain.prediction_directory import find_prediction_files, record_assembly_ids


def test_find_pred_files(tmp_path):
    (tmp_path / 'GCA_013146725.pred').write_text('')
    (tmp_path / 'GCF_000013305.pred.bz2').write_bytes(bz2.compress(b''))
    (tmp_path / 'notes.txt').write_text('')
    assert set(find_prediction_files(tmp_path)) == {'GCA_013146725', 'GCF_000013305'}


def test_duplicate_assembly_fails(tmp_path):
    (tmp_path / 'GCA_013146725.pred').touch()
    (tmp_path / 'GCA_013146725.pred.bz2').touch()
    with pytest.raises(ValueError, match='Multiple'):
        find_prediction_files(tmp_path)


def test_explicit_assembly_metadata():
    record = SimpleNamespace(dbxrefs=['Assembly:GCA_013146725.1'], annotations={})
    assert record_assembly_ids(record) == {'GCA_013146725'}
    assert record_assembly_ids(SimpleNamespace(dbxrefs=[], annotations={})) == set()
