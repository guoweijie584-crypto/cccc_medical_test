import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cccc.kernel.group_template import parse_group_template

from config.cccc_native.blueprints import (
    build_evaluation_group_template,
    build_help_markdown_for_evaluation_group,
    build_help_markdown_for_main_group,
    build_main_group_template,
)


def test_main_group_template_is_valid():
    template = parse_group_template(build_main_group_template(runtime="codex"))
    assert template.title == "glucose-management-main"
    assert [actor.actor_id for actor in template.actors] == [
        "primary",
        "pharmacist",
        "nutritionist",
        "doctor",
        "memory",
    ]


def test_evaluation_group_template_is_valid():
    template = parse_group_template(build_evaluation_group_template(runtime="codex"))
    assert template.title == "glucose-management-eval"
    assert [actor.actor_id for actor in template.actors] == [
        "evaluator",
        "analyzer",
        "prompt_optimizer",
        "memory_optimizer",
    ]


def test_guidance_front_matter_removed():
    main_help = build_help_markdown_for_main_group()
    eval_help = build_help_markdown_for_evaluation_group()
    assert not main_help.lstrip().startswith("---")
    assert not eval_help.lstrip().startswith("---")
    assert "## @actor:primary" in main_help
    assert "## @actor:evaluator" in eval_help
