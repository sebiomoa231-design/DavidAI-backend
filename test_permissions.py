from david.security.permissions import PermissionRequest, evaluate_permission, PermissionDecision


def test_sensitive_action_requires_confirmation():
    result = evaluate_permission(PermissionRequest(action="delete_account", category="delete"))
    assert result.decision == PermissionDecision.ASK


def test_confirmed_sensitive_action_is_allowed():
    result = evaluate_permission(PermissionRequest(action="delete_account", category="delete", confirmed=True))
    assert result.decision == PermissionDecision.ALLOW


def test_normal_action_is_allowed():
    result = evaluate_permission(PermissionRequest(action="list_projects", category="read"))
    assert result.decision == PermissionDecision.ALLOW
