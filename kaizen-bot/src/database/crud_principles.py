"""
CRUD операции для системы оценки принципов жизни

Flow оценки: 5 дней по 5 принципов
- День 1: принципы 1-5
- День 2: принципы 6-10
- День 3: принципы 11-15
- День 4: принципы 16-20
- День 5: принципы 21-25 → итоговый отчёт + награда
"""
from datetime import datetime, date
from src.database.models import (
    LifePrinciple, MonthlyAssessment, PrincipleRating, User,
    get_session
)


# 25 принципов из my_standart.rst
LIFE_PRINCIPLES = [
    "Я строю системы во всех сферах жизни (учёба, бизнес, здоровье)",
    "Я уделяю особое внимание образованию (HSE + IELTS)",
    "Я поддерживаю баланс между учёбой, работой и личной жизнью",
    "Мои цели в академической сфере и бизнесе мотивируют меня",
    "Я всегда выполняю взятые на себя обязательства",
    "Я поддерживаю связь с семьёй",
    "Я развиваю дисциплину через регулярные тренировки 3 раза в неделю",
    "Я уделяю качественное время своим отношениям (1 день в неделю)",
    "Я ценю и уважаю отношения, создавая эмоциональную близость",
    "Я горжусь своей фамилией и держу высокую планку",
    "Я регулярно тренируюсь, поддерживая физическое и психологическое здоровье",
    "Я принимаю решения, основываясь на внутренней гармонии",
    "Я поддерживаю ресурсное состояние, чередуя работу с отдыхом",
    "Я проявляю уважение ко всем людям независимо от их статуса",
    "Я уверенно отстаиваю свои принципы, сохраняя достоинство",
    "Я предпочитаю прямую коммуникацию",
    "Я даю обратную связь только когда она необходима и конструктивна",
    "Я развиваю бизнес-проекты, основанные на честности и инновациях",
    "Моя семья — источник силы и вдохновения",
    "Я создаю проекты для своего развития и улучшения жизни окружающих",
    "Моё наследие — пример совмещения учёбы, саморазвития и бизнеса",
    "Я поддерживаю свой внешний вид и следую распорядку дня (подъём 6:30-7:00)",
    "Моё расписание сбалансировано для учёбы, работы и отдыха",
    "Я строю полезные связи с единомышленниками",
    "Я расширяю кругозор через образование и саморазвитие",
]


# ============ ИНИЦИАЛИЗАЦИЯ ПРИНЦИПОВ ============

def init_default_principles():
    """Инициализация 25 принципов (вызывается при старте бота)"""
    session = get_session()
    try:
        existing = session.query(LifePrinciple).count()
        if existing == 0:
            for i, text in enumerate(LIFE_PRINCIPLES, 1):
                principle = LifePrinciple(number=i, text=text)
                session.add(principle)
            session.commit()
            print(f"[INIT] Added {len(LIFE_PRINCIPLES)} life principles")
    finally:
        session.close()


def get_all_principles() -> list[LifePrinciple]:
    """Получить все активные принципы"""
    session = get_session()
    try:
        return session.query(LifePrinciple).filter(
            LifePrinciple.is_active == True
        ).order_by(LifePrinciple.number).all()
    finally:
        session.close()


def get_principle(principle_id: int) -> LifePrinciple | None:
    """Получить принцип по ID"""
    session = get_session()
    try:
        return session.query(LifePrinciple).filter(
            LifePrinciple.id == principle_id
        ).first()
    finally:
        session.close()


def get_principles_for_day(day: int) -> list[LifePrinciple]:
    """
    Получить 5 принципов для определённого дня оценки.
    День 1: принципы 1-5
    День 2: принципы 6-10
    и т.д.
    """
    start_num = (day - 1) * 5 + 1  # 1, 6, 11, 16, 21
    end_num = day * 5              # 5, 10, 15, 20, 25

    session = get_session()
    try:
        return session.query(LifePrinciple).filter(
            LifePrinciple.is_active == True,
            LifePrinciple.number >= start_num,
            LifePrinciple.number <= end_num
        ).order_by(LifePrinciple.number).all()
    finally:
        session.close()


# ============ MONTHLY ASSESSMENT ============

def get_or_create_monthly_assessment(user_id: int, year: int = None, month: int = None) -> MonthlyAssessment:
    """Получить или создать assessment для текущего месяца"""
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month

    session = get_session()
    try:
        assessment = session.query(MonthlyAssessment).filter(
            MonthlyAssessment.user_id == user_id,
            MonthlyAssessment.year == year,
            MonthlyAssessment.month == month
        ).first()

        if not assessment:
            assessment = MonthlyAssessment(
                user_id=user_id,
                year=year,
                month=month,
                current_day=1
            )
            session.add(assessment)
            session.commit()
            session.refresh(assessment)

        return assessment
    finally:
        session.close()


def get_current_assessment(user_id: int) -> MonthlyAssessment | None:
    """Получить текущий незавершённый assessment"""
    today = date.today()
    session = get_session()
    try:
        return session.query(MonthlyAssessment).filter(
            MonthlyAssessment.user_id == user_id,
            MonthlyAssessment.year == today.year,
            MonthlyAssessment.month == today.month,
            MonthlyAssessment.completed == False
        ).first()
    finally:
        session.close()


def get_last_completed_assessment(user_id: int) -> MonthlyAssessment | None:
    """Получить последнюю завершённую оценку"""
    session = get_session()
    try:
        return session.query(MonthlyAssessment).filter(
            MonthlyAssessment.user_id == user_id,
            MonthlyAssessment.completed == True
        ).order_by(
            MonthlyAssessment.year.desc(),
            MonthlyAssessment.month.desc()
        ).first()
    finally:
        session.close()


def advance_assessment_day(assessment_id: int) -> MonthlyAssessment:
    """Перейти к следующему дню оценки"""
    session = get_session()
    try:
        assessment = session.query(MonthlyAssessment).filter(
            MonthlyAssessment.id == assessment_id
        ).first()

        if assessment and assessment.current_day < 5:
            assessment.current_day += 1
            session.commit()
            session.refresh(assessment)

        return assessment
    finally:
        session.close()


def complete_assessment(assessment_id: int) -> MonthlyAssessment:
    """Завершить assessment и посчитать среднюю оценку"""
    session = get_session()
    try:
        assessment = session.query(MonthlyAssessment).filter(
            MonthlyAssessment.id == assessment_id
        ).first()

        if assessment:
            ratings = session.query(PrincipleRating).filter(
                PrincipleRating.assessment_id == assessment_id
            ).all()

            if ratings:
                avg = sum(r.score for r in ratings) / len(ratings)
                assessment.average_score = int(avg * 10)  # 0-100

            assessment.completed = True
            assessment.completed_at = datetime.now()
            session.commit()
            session.refresh(assessment)

        return assessment
    finally:
        session.close()


# ============ PRINCIPLE RATINGS ============

def save_principle_rating(assessment_id: int, principle_id: int, score: int) -> PrincipleRating:
    """Сохранить оценку принципа"""
    session = get_session()
    try:
        existing = session.query(PrincipleRating).filter(
            PrincipleRating.assessment_id == assessment_id,
            PrincipleRating.principle_id == principle_id
        ).first()

        if existing:
            existing.score = score
            session.commit()
            session.refresh(existing)
            return existing
        else:
            rating = PrincipleRating(
                assessment_id=assessment_id,
                principle_id=principle_id,
                score=score
            )
            session.add(rating)
            session.commit()
            session.refresh(rating)
            return rating
    finally:
        session.close()


def get_ratings_for_day(assessment_id: int, day: int) -> list[PrincipleRating]:
    """Получить оценки для определённого дня"""
    principles = get_principles_for_day(day)
    principle_ids = [p.id for p in principles]

    session = get_session()
    try:
        return session.query(PrincipleRating).filter(
            PrincipleRating.assessment_id == assessment_id,
            PrincipleRating.principle_id.in_(principle_ids)
        ).all()
    finally:
        session.close()


def get_all_ratings(assessment_id: int) -> list[PrincipleRating]:
    """Получить все оценки для assessment"""
    session = get_session()
    try:
        return session.query(PrincipleRating).filter(
            PrincipleRating.assessment_id == assessment_id
        ).all()
    finally:
        session.close()


def count_rated_principles(assessment_id: int) -> int:
    """Подсчитать количество оценённых принципов"""
    session = get_session()
    try:
        return session.query(PrincipleRating).filter(
            PrincipleRating.assessment_id == assessment_id
        ).count()
    finally:
        session.close()


# ============ АНАЛИТИКА ============

def get_problem_zones(assessment_id: int, threshold: int = 7) -> list[dict]:
    """Получить проблемные зоны (оценка < threshold)"""
    session = get_session()
    try:
        ratings = session.query(PrincipleRating).filter(
            PrincipleRating.assessment_id == assessment_id,
            PrincipleRating.score < threshold
        ).all()

        result = []
        for rating in ratings:
            principle = session.query(LifePrinciple).filter(
                LifePrinciple.id == rating.principle_id
            ).first()
            if principle:
                result.append({
                    "number": principle.number,
                    "text": principle.text,
                    "score": rating.score
                })

        return sorted(result, key=lambda x: x["score"])
    finally:
        session.close()


def get_success_zones(assessment_id: int, threshold: int = 9) -> list[dict]:
    """Получить успешные зоны (оценка >= threshold)"""
    session = get_session()
    try:
        ratings = session.query(PrincipleRating).filter(
            PrincipleRating.assessment_id == assessment_id,
            PrincipleRating.score >= threshold
        ).all()

        result = []
        for rating in ratings:
            principle = session.query(LifePrinciple).filter(
                LifePrinciple.id == rating.principle_id
            ).first()
            if principle:
                result.append({
                    "number": principle.number,
                    "text": principle.text,
                    "score": rating.score
                })

        return sorted(result, key=lambda x: -x["score"])
    finally:
        session.close()


def compare_with_previous(user_id: int, current_assessment_id: int) -> dict:
    """Сравнить текущую оценку с предыдущей"""
    session = get_session()
    try:
        current = session.query(MonthlyAssessment).filter(
            MonthlyAssessment.id == current_assessment_id
        ).first()

        if not current:
            return {"has_previous": False}

        previous = session.query(MonthlyAssessment).filter(
            MonthlyAssessment.user_id == user_id,
            MonthlyAssessment.completed == True,
            MonthlyAssessment.id != current_assessment_id
        ).order_by(
            MonthlyAssessment.year.desc(),
            MonthlyAssessment.month.desc()
        ).first()

        if not previous:
            return {"has_previous": False}

        current_avg = current.average_score / 10 if current.average_score else 0
        previous_avg = previous.average_score / 10 if previous.average_score else 0

        return {
            "has_previous": True,
            "current_avg": current_avg,
            "previous_avg": previous_avg,
            "diff": current_avg - previous_avg,
            "previous_month": previous.month,
            "previous_year": previous.year
        }
    finally:
        session.close()


def get_assessment_history(user_id: int, limit: int = 6) -> list[MonthlyAssessment]:
    """Получить историю оценок"""
    session = get_session()
    try:
        return session.query(MonthlyAssessment).filter(
            MonthlyAssessment.user_id == user_id,
            MonthlyAssessment.completed == True
        ).order_by(
            MonthlyAssessment.year.desc(),
            MonthlyAssessment.month.desc()
        ).limit(limit).all()
    finally:
        session.close()
