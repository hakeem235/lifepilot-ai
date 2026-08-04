"""Seed the system preset routines (Issue 9.1).

These are global templates (user=None) available to everyone. Reversible: the
reverse deletes exactly the presets it created, by name.
"""

from django.db import migrations

PRESETS = [
    (
        "Morning Routine",
        "🌅",
        [
            ("Hydrate + stretch", "medium", 7 * 60),
            ("Journal / plan the day", "high", 7 * 60 + 30),
            ("Focused deep work", "high", 8 * 60),
        ],
    ),
    (
        "Deep Work",
        "🎯",
        [
            ("Silence notifications", "medium", 9 * 60),
            ("Deep work block 1", "high", 9 * 60 + 15),
            ("Short break", "low", 10 * 60 + 45),
            ("Deep work block 2", "high", 11 * 60),
        ],
    ),
    (
        "Evening Wind-down",
        "🌙",
        [
            ("Review tomorrow's tasks", "medium", 20 * 60),
            ("Screens off", "medium", 21 * 60),
            ("Read / relax", "low", 21 * 60 + 30),
        ],
    ),
    (
        "Workout",
        "💪",
        [
            ("Warm-up", "low", 18 * 60),
            ("Main session", "high", 18 * 60 + 15),
            ("Cool-down + stretch", "medium", 19 * 60),
        ],
    ),
]


def seed(apps, schema_editor):
    TaskTemplate = apps.get_model("routines", "TaskTemplate")
    TemplateItem = apps.get_model("routines", "TemplateItem")
    for name, icon, items in PRESETS:
        template, _ = TaskTemplate.objects.get_or_create(
            name=name, user=None, defaults={"icon": icon}
        )
        for order, (title, priority, offset) in enumerate(items):
            TemplateItem.objects.get_or_create(
                template=template,
                title=title,
                defaults={"priority": priority, "order": order, "time_offset_minutes": offset},
            )


def unseed(apps, schema_editor):
    TaskTemplate = apps.get_model("routines", "TaskTemplate")
    TaskTemplate.objects.filter(
        user=None, name__in=[name for name, _, _ in PRESETS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("routines", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
