"""Provider sequence proof is read-only and never based on local audio length."""


import pytest

from downtify import recording_equivalence as module
from downtify import spotify
from downtify.recording_equivalence import RecordingEquivalenceRegistry

A, B = 'A' * 22, 'B' * 22


def sequence(prefix):
    return [
        dict(
            song_id=(prefix + str(i)).ljust(22, 'x'),
            name=name,
            artists=['Artist', 'Guest'],
            artists_structured=True,
            album_artist='Artist',
            album_name='Title',
            duration=180 + i,
            explicit=False,
            disc_number=1,
            track_number=i + 1,
            album_track_total=2,
        )
        for i, name in enumerate(['First', 'Second'])
    ]


def test_complete_sequences_prove_only_corresponding_recording_ids():
    registry = RecordingEquivalenceRegistry()
    first, second = sequence('a'), sequence('b')
    assert registry.add(A, first)
    assert registry.add(B, second)
    assert registry.equivalent_tracks(first[0]['song_id']) == {
        first[0]['song_id'],
        second[0]['song_id'],
    }
    assert second[1]['song_id'] not in registry.equivalent_tracks(
        first[0]['song_id']
    )


@pytest.mark.parametrize(
    'change',
    [
        'partial',
        'explicit',
        'duration',
        'credits',
        'version',
        'order',
        'opaque',
    ],
)
def test_partial_or_semantically_different_sequences_never_equate(change):
    registry = RecordingEquivalenceRegistry()
    first, changed = sequence('a'), sequence('b')
    registry.add(A, first)
    if change == 'partial':
        changed = changed[:1]
    elif change == 'explicit':
        changed[1]['explicit'] = True
    elif change == 'duration':
        changed[1]['duration'] += 1
    elif change == 'credits':
        changed[1]['artists'] = ['Other']
    elif change == 'version':
        changed[1]['album_name'] += ' +'
    elif change == 'order':
        changed.reverse()
    else:
        changed[1]['artists_structured'] = False
    registry.add(B, changed)
    assert registry.equivalent_tracks(first[0]['song_id']) == {
        first[0]['song_id']
    }


def test_conflicting_refetch_revokes_old_equivalence():
    registry = RecordingEquivalenceRegistry()
    first, second = sequence('a'), sequence('b')
    registry.add(A, first)
    registry.add(B, second)
    registry.add(B, second[:1])
    assert registry.equivalent_tracks(first[0]['song_id']) == {
        first[0]['song_id']
    }


def test_warm_source_lookup_fetches_one_owned_edition_without_writes(
    monkeypatch,
):

    registry = RecordingEquivalenceRegistry()
    monkeypatch.setattr(module, 'registry', registry)
    first, second = sequence('a'), sequence('b')
    calls = []

    class Index:
        @staticmethod
        def identities_for_files(files):
            assert files == {'one.mp3'}
            return {'one.mp3': {first[0]['song_id']}}

    monkeypatch.setattr(
        spotify, '_album_ref_from_open_track_page', lambda tid: (A, 1)
    )
    monkeypatch.setattr(
        spotify, 'album_tracks_from_id', lambda aid: calls.append(aid) or first
    )
    result = dict(status='resolved', edition=B, tracks=second)
    entries = [dict(file='one.mp3', album='Title', album_artist='Artist')]
    module.warm_source_equivalence(result, entries, Index())
    module.warm_source_equivalence(result, entries, Index())
    assert calls == [A]
    assert registry.equivalent_tracks(second[0]['song_id']) == {
        first[0]['song_id'],
        second[0]['song_id'],
    }


def test_bounded_registry_drops_old_proofs():
    registry = RecordingEquivalenceRegistry(max_albums=1)
    first, second = sequence('a'), sequence('b')
    registry.add(A, first)
    registry.add(B, second)
    assert registry.equivalent_tracks(first[0]['song_id']) == {
        first[0]['song_id']
    }
