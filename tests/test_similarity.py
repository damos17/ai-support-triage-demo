from app.similarity import TokenCosineSimilarity


def test_related_incident_messages_score_higher_than_unrelated_messages():
    engine = TokenCosineSimilarity()
    related = engine.score(
        "Our data imports stopped and are failing with timeout errors.",
        "Data imports stopped and are failing with repeated timeout errors.",
    )
    unrelated = engine.score(
        "Our data imports stopped and are failing with timeout errors.",
        "Where can I change notification settings for the workspace?",
    )
    assert related > unrelated
    assert related >= 0.45


def test_similarity_supports_russian_text():
    engine = TokenCosineSimilarity()
    related = engine.score(
        "Импорт данных остановился и падает по тайм-ауту.",
        "Импорт данных снова остановился из-за тайм-аута.",
    )
    unrelated = engine.score(
        "Импорт данных остановился и падает по тайм-ауту.",
        "Где изменить настройки уведомлений?",
    )
    assert related > unrelated
