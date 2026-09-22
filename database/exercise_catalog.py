"""Built-in exercise-to-muscle catalog.

Unknown user exercises stay unmapped and are shown as «Не определено».
Aliases are stored as extra catalog rows so lookup can be case/ё insensitive.
"""

# (aliases, ((muscle_slug, contribution), ...))
EXERCISE_MUSCLE_CATALOG = (
    (
        ("жим лежа", "жим лёжа", "bench press", "bench", "жим штанги лежа"),
        (("chest", 1.0), ("triceps", 0.5), ("shoulders", 0.3)),
    ),
    (
        ("жим гантелей", "жим гантелей лежа", "dumbbell press", "dumbbell bench"),
        (("chest", 1.0), ("triceps", 0.5), ("shoulders", 0.3)),
    ),
    (
        ("разводка", "разведение гантелей", "pec fly", "fly", "бабочка"),
        (("chest", 1.0), ("shoulders", 0.3)),
    ),
    (
        ("кроссовер", "crossover", "сведение в кроссовере"),
        (("chest", 1.0), ("shoulders", 0.3)),
    ),
    (
        ("отжимания", "отжимание", "push ups", "push-ups"),
        (("chest", 1.0), ("triceps", 0.5), ("shoulders", 0.3)),
    ),
    (
        ("брусья", "отжимания на брусьях", "dips"),
        (("chest", 1.0), ("triceps", 0.7), ("shoulders", 0.3)),
    ),
    (
        ("подтягивания", "подтягивание", "pull ups", "pull-ups", "pullup"),
        (("back", 1.0), ("biceps", 0.5)),
    ),
    (
        ("тяга верхнего блока", "тяга блока", "lat pulldown", "pulldown"),
        (("back", 1.0), ("biceps", 0.5)),
    ),
    (
        ("тяга горизонтального блока", "тяга к поясу на блоке", "seated row"),
        (("back", 1.0), ("biceps", 0.4)),
    ),
    (
        ("тяга штанги", "тяга штанги в наклоне", "bent over row", "штанга в наклоне"),
        (("back", 1.0), ("biceps", 0.4)),
    ),
    (
        ("тяга гантели", "тяга гантели в наклоне", "one arm row"),
        (("back", 1.0), ("biceps", 0.4)),
    ),
    (
        ("тяга т-грифа", "t-bar row", "т-гриф"),
        (("back", 1.0), ("biceps", 0.4)),
    ),
    (
        ("пуловер", "pullover"),
        (("back", 1.0), ("chest", 0.4)),
    ),
    (
        ("шраги", "shrugs"),
        (("back", 1.0), ("shoulders", 0.3)),
    ),
    (
        ("становая", "становая тяга", "deadlift"),
        (("back", 1.0), ("hamstrings", 0.7), ("glutes", 0.7), ("quadriceps", 0.3)),
    ),
    (
        ("румынская тяга", "рдл", "rdl", "румынская"),
        (("hamstrings", 1.0), ("glutes", 0.7), ("back", 0.4)),
    ),
    (
        ("армейский жим", "жим стоя", "overhead press", "ohp", "жим штанги стоя"),
        (("shoulders", 1.0), ("triceps", 0.5)),
    ),
    (
        ("жим гантелей сидя", "жим гантелей стоя", "shoulder press"),
        (("shoulders", 1.0), ("triceps", 0.5)),
    ),
    (
        ("махи", "махи гантелями", "lateral raise", "разведения в стороны"),
        (("shoulders", 1.0),),
    ),
    (
        ("разведения в наклоне", "махи в наклоне", "rear delt fly"),
        (("shoulders", 1.0), ("back", 0.3)),
    ),
    (
        ("протяжка", "upright row"),
        (("shoulders", 1.0), ("back", 0.4)),
    ),
    (
        ("подъем на бицепс", "сгибания на бицепс", "бицепс", "bicep curl", "curl"),
        (("biceps", 1.0), ("forearms", 0.3)),
    ),
    (
        ("молотки", "молотковые сгибания", "hammer curl"),
        (("biceps", 1.0), ("forearms", 0.5)),
    ),
    (
        ("французский жим", "french press", "skull crusher"),
        (("triceps", 1.0),),
    ),
    (
        ("разгибания на блоке", "трицепс на блоке", "triceps pushdown"),
        (("triceps", 1.0),),
    ),
    (
        ("присед", "приседания", "squat", "приседания со штангой"),
        (("quadriceps", 1.0), ("glutes", 0.7), ("hamstrings", 0.4)),
    ),
    (
        ("жим ногами", "leg press"),
        (("quadriceps", 1.0), ("glutes", 0.5)),
    ),
    (
        ("выпады", "lunge", "lunges"),
        (("quadriceps", 1.0), ("glutes", 0.7)),
    ),
    (
        ("разгибания ног", "разгибание ног", "leg extension"),
        (("quadriceps", 1.0),),
    ),
    (
        ("сгибания ног", "сгибание ног", "leg curl"),
        (("hamstrings", 1.0),),
    ),
    (
        ("икры", "подъемы на носки", "calf raise"),
        (("calves", 1.0),),
    ),
    (
        ("гакк", "гакк-приседания", "hack squat"),
        (("quadriceps", 1.0), ("glutes", 0.4)),
    ),
    (
        ("ягодичный мост", "хип траст", "hip thrust"),
        (("glutes", 1.0), ("hamstrings", 0.4)),
    ),
    (
        ("скручивания", "пресс", "crunch", "crunches"),
        (("core", 1.0),),
    ),
    (
        ("планка", "plank"),
        (("core", 1.0),),
    ),
    (
        ("подъемы ног", "подъём ног", "leg raises"),
        (("core", 1.0),),
    ),
)
