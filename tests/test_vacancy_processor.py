from unittest.mock import MagicMock

import pytest

from app.exceptions import LoadingError
from app.vacancy_processor import VacancyProcessor


@pytest.fixture
def mock_ai_client():
    return MagicMock()


@pytest.fixture
def processor(tmp_path, mock_ai_client):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python developer with 1 year experience.", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Example response.", encoding="utf-8")
    return VacancyProcessor(
        ai_client=mock_ai_client,
        resume_path=str(resume),
        prompt_path=str(prompt),
        correct_professions=["python developer"],
    )


def test_is_correct_profession_yes(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "да"
    result = processor.is_correct_profession("Vacancy for Python developer")
    assert result is True


def test_is_correct_profession_no(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "нет"
    result = processor.is_correct_profession("Vacancy for Java developer")
    assert result is False


def test_is_correct_profession_avoids_false_positive(processor, mock_ai_client):
    # Ранее "да" внутри "нет, даже близко" давало True
    mock_ai_client.get_response.return_value = "нет, даже близко не подходит"
    result = processor.is_correct_profession("Vacancy for Java developer")
    assert result is False


def test_is_correct_profession_yes_with_punctuation(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "да!"
    result = processor.is_correct_profession("Vacancy for Python developer")
    assert result is True


def test_generate_response_success(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "Generated cover letter"
    result = processor.generate_response(
        vacancy_title="Python Dev",
        vacancy_description="We need Python developer",
    )
    assert result == "Generated cover letter"
    mock_ai_client.get_response.assert_called_once()
    call_args = mock_ai_client.get_response.call_args[0][0]
    assert "Python Dev" in call_args
    assert "We need Python developer" in call_args


def test_init_missing_resume_raises(tmp_path, mock_ai_client):
    missing_resume = tmp_path / "no_resume.txt"
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Example", encoding="utf-8")
    with pytest.raises(LoadingError):
        VacancyProcessor(
            ai_client=mock_ai_client,
            resume_path=str(missing_resume),
            prompt_path=str(prompt),
        )


def test_is_correct_profession_no_filter_when_none(tmp_path, mock_ai_client):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python developer with 1 year experience.", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Example response.", encoding="utf-8")
    processor = VacancyProcessor(
        ai_client=mock_ai_client,
        resume_path=str(resume),
        prompt_path=str(prompt),
        correct_professions=None,
        grade_levels=None,
    )
    result = processor.is_correct_profession("Vacancy for Java developer")
    assert result is True
    mock_ai_client.get_response.assert_not_called()


def test_is_correct_profession_grade_levels_in_prompt(tmp_path, mock_ai_client):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python developer with 1 year experience.", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Example response.", encoding="utf-8")
    processor = VacancyProcessor(
        ai_client=mock_ai_client,
        resume_path=str(resume),
        prompt_path=str(prompt),
        correct_professions=["python developer"],
        grade_levels=["junior", "middle"],
    )
    mock_ai_client.get_response.return_value = "да"
    processor.is_correct_profession("Vacancy for Python developer")
    call_args = mock_ai_client.get_response.call_args[0][0]
    assert "junior" in call_args
    assert "middle" in call_args
    assert "уровня" in call_args


def test_is_correct_profession_grade_only_calls_ai(tmp_path, mock_ai_client):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python developer with 1 year experience.", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Example response.", encoding="utf-8")
    processor = VacancyProcessor(
        ai_client=mock_ai_client,
        resume_path=str(resume),
        prompt_path=str(prompt),
        correct_professions=None,
        grade_levels=["senior"],
    )
    mock_ai_client.get_response.return_value = "да"
    result = processor.is_correct_profession("Vacancy for Senior Python developer")
    assert result is True
    mock_ai_client.get_response.assert_called_once()
    call_args = mock_ai_client.get_response.call_args[0][0]
    assert "senior" in call_args
    assert "уровня" in call_args


def test_is_correct_profession_caches_result(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "да"
    processor.is_correct_profession("Vacancy for Python developer")
    processor.is_correct_profession("Vacancy for Python developer")
    assert mock_ai_client.get_response.call_count == 1


def test_generate_response_caches_result(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "Generated cover letter"
    processor.generate_response("Python Dev", "We need Python developer")
    processor.generate_response("Python Dev", "We need Python developer")
    assert mock_ai_client.get_response.call_count == 1


def test_is_correct_profession_uses_system_prompt(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "да"
    processor.is_correct_profession("Vacancy for Python developer")
    _, kwargs = mock_ai_client.get_response.call_args
    assert "system_prompt" in kwargs
    assert "да" in kwargs["system_prompt"].lower()
    assert "нет" in kwargs["system_prompt"].lower()


def test_generate_response_uses_system_prompt(processor, mock_ai_client):
    mock_ai_client.get_response.return_value = "Generated cover letter"
    processor.generate_response("Python Dev", "We need Python developer")
    _, kwargs = mock_ai_client.get_response.call_args
    assert "system_prompt" in kwargs
    assert "сопроводительные" in kwargs["system_prompt"].lower()


def test_is_correct_profession_custom_professions_in_prompt(tmp_path, mock_ai_client):
    resume = tmp_path / "resume.txt"
    resume.write_text("Python developer with 1 year experience.", encoding="utf-8")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Example response.", encoding="utf-8")
    processor = VacancyProcessor(
        ai_client=mock_ai_client,
        resume_path=str(resume),
        prompt_path=str(prompt),
        correct_professions=["go developer", "rust разработчик"],
    )
    mock_ai_client.get_response.return_value = "да"
    processor.is_correct_profession("Vacancy for Go developer")
    call_args = mock_ai_client.get_response.call_args[0][0]
    assert "go developer" in call_args
    assert "rust разработчик" in call_args
