from pydantic import (
    BaseModel,
    validator,
    root_validator,
    PydanticValueError,
    conint,
    FileUrl
    )

from typing import List
from enum import IntEnum
from datetime import date, time, timedelta
from calendar import (MONDAY,
                      TUESDAY,
                      WEDNESDAY,
                      THURSDAY,
                      FRIDAY,
                      SATURDAY,
                      SUNDAY)


class Weekdays(IntEnum):
    monday = MONDAY
    tuesday = TUESDAY
    wednesday = WEDNESDAY
    thursday = THURSDAY
    friday = FRIDAY
    saturday = SATURDAY
    sunday = SUNDAY


class SelectiveAssigningError(PydanticValueError):
    """
    Raise this error, when one must assign at least one of two parameters
    :param selection0: one of selective parameters
    :param selection1: one of selective parameters
    """

    code = 'selective_assigning_error'
    msg_template = ('You must assign at least one of '
                    '"{selection0}" or "{selection1}"')


class DependentAssigningError(PydanticValueError):
    """
    Raise this error, when one field value depends on another field value.
    :param fields: string of fields list, which values depend on other fields
            values.
    :param depend_on: string of fields list, on which values depend values of
            fields above.
    """

    code = 'dependent_assigning_error'
    msg_template = ('Value(s) of field(s) {fields} depend(s) on value(s) of '
                    'field(s) {depend_on}')


class TimeInterval(BaseModel):
    """
    Временной интервал рабочего дня, представленный двумя параметрами:
    :param start_time: time: начало временного интервала
    :param finish_time: time конец временного интервала (должен быть
                позже начала!)
    """

    start_time: time = time.min
    finish_time: time = time.max

    @validator('finish_time')
    def finish_must_be_later(cls, ft, values):
        if ft - values['start_time'] <= 0:
            raise ValueError('Finish time must be later then start time')
        else:
            return ft


class WorkDay(BaseModel):
    """
    Объект, описывающий рабочий день.
    :param weekday*: Weekdays день недели int или можно использовать константы
                из модуля calendar, 0 - MONDAY и т.д.
    :param working_hours: List[TimeInterval] список интервалов рабочего времени
    :param lunch_hours: TimeInterval обеденный перерыв при наличии
    :param is_absent: bool для явного указания нерабочего дня, по-умолчанию
                False, при этом обязательно задание значения рабочего времени,
                иначе не обязательно.
    """

    weekday: Weekdays
    working_hours: List[TimeInterval] | None
    lunch_hours: TimeInterval | None
    is_absent: bool = False

    @validator('is_absent')
    def time_none_only_if_is_absent(cls, v, values):
        if 'working_hours' in values and 'lunch_hours' in values \
                and values['working_hours'] is None \
                and not v:
            raise DependentAssigningError(fields='working_hours, lunch_hours',
                                          depend_on='is_absent')


class Schedule(BaseModel):
    """
    Расписание рабочей недели -- список объектов рабочего дня, длиной не более
    7 дней. При этом не обязательно задавать все 7 дней, можно ограничиться
    только рабочими. Объект создаётся независимо от специалиста и впоследствии
    может быть к нему привязан через свой идентификатор.
    :param id: int идентификатор объекта расписание
    :param working_days: List[WorkDay] список рабочих дней длиной не более 7.
    """

    id: int
    working_days: List[WorkDay]

    @validator('working_days')
    def max_len_7_days(cls, w):
        if len(w) > 7:
            raise ValueError("There are only 7 days in a week!")


class Vacation(BaseModel):
    """
    Объект, описывающий отпуск. Можно задать либо длительность, либо дату
    окончания отпуска, но обязательно задать что-то одно. Если заданы оба
    параметра, то приоритет отдаётся длительности отпуска, и значение
    даты окончания выставляется (перезадаётся автоматически) по ней.
    :param start_date*: date обязательный параметр начало отпуска
    :param finish_date: date приоритетный опциональный параметр дата окончания
                отпуска
    :param vacation_duration: timedelta опциональный параметр длительность
                отпуска. Должен быть задан либо этот, либо предыдущий параметр,
                но ОБЯЗАТЕЛЬНО один из них, либо оба, тогда этот будет
                перезадан согласно finish_data.
    """

    start_date: date
    finish_date: date | None = None
    vacation_duration: (timedelta
                        | conint(strict=True, gt=0, le=35)
                        | None) = None

    @validator('vacation_duration', always=True)
    def duration_processing(cls, d, values: dict):
        if ('finish_date' not in values or not values['finish_date']) \
                and not d:
            raise SelectiveAssigningError(
                    selection0='finish_date',
                    selection1='vacation_duration')
        if 'finish_date' in values and 'start_date' in values:
            return values['finish_date'] - values['start_date']
        else:
            if d is int:
                d = timedelta(days=d)

            return d

    @root_validator
    def redefine_duration(cls, values):
        if 'vacation_duration' in values and values.get('vacation_duration') \
                and \
                ('finish_date' not in values or not values.get('finish_date')):

            f_date = values.get('start_date') + values.get('vacation_duration')
            values.update({'finish_date': f_date})

        return values


class Department(BaseModel):
    """
    Описывает отдел
    :param id: int
    :param name: str название отдела
    """

    id: int
    name: str


class Position(BaseModel):
    """
    Описывает должность
    :param id: int
    :param name: str название должности
    """

    id: int
    name: str


class Specialist(BaseModel):
    """
    Объект, описывающий специалиста.
    :param id: int
    :param first_name: str Имя
    :param last_name: str Фамилия
    :param patronymic: str Отчество
    :param photo: FileUrl путь к файлу фотографии
    :param department_id: int ИД отдела
    :param position_id: int ИД должности
    :param description: str описание специалиста (научное звание, квалификация)
    :param schedule_id: int ИД расписания
    :param vacation: Vacation отпуск
    :parameter full_name: str readonly ФИО полностью одной строкой
    """

    id: int
    first_name: str
    last_name: str
    patronymic: str
    photo: FileUrl

    department_id: int
    position_id: int

    description: str | None

    schedule_id: int
    vacation: Vacation | None

    @property
    def full_name(self):
        return ' '.join((self.last_name, self.first_name, self.patronymic))

    @validator('first_name', 'last_name', 'patronymic', pre=True)
    def must_have_only_letters(cls, v):
        if not v.isalpha():
            raise ValueError("must contain only letters.")
        return v.title()

    @validator('schedule_id', 'department_id', 'position_id')
    def must_be_ge_zero(cls, v):
        if v < 0:
            return None

        return v
