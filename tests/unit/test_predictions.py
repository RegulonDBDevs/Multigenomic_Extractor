from pathlib import Path
from types import SimpleNamespace
from multigenomic_extractor.domain.predictions import read_predictions, build_protein_gene_index, resolve_prediction


def test_reader(tmp_path):
    path = tmp_path / 'test.pred'
    path.write_text('### cutoff=-0.197\n# Strand\tTU\tGeneNames\nF\tP1,P2\ta,b\n')
    predictions = read_predictions(path)
    assert len(predictions) == 1
    assert predictions[0].protein_ids == ('P1', 'P2')


def test_index_and_resolution():
    def feature(kind, qualifiers, start, end):
        return SimpleNamespace(type=kind, qualifiers=qualifiers, location=SimpleNamespace(start=start, end=end, strand=1))
    record = SimpleNamespace(id='NZ_TEST.1', features=[
        feature('gene', {'locus_tag': ['L1'], 'gene': ['a']}, 10, 20),
        feature('CDS', {'locus_tag': ['L1'], 'protein_id': ['P1']}, 10, 20),
    ])
    index, warnings = build_protein_gene_index(record, {'L1': 'RDBMGECOLIGN0000001'})
    assert not warnings
    prediction = read_prediction = __import__('multigenomic_extractor.domain.predictions', fromlist=['Prediction']).Prediction('forward', ('P1',), ('a',), 3)
    assert resolve_prediction(prediction, index)[0]['gene_id'] == 'RDBMGECOLIGN0000001'
