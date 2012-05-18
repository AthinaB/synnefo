from django import template

register = template.Library()

@register.filter(name="vm_public_ip")
def vm_public_ip(vm):
    """
    Identify if vm is connected to ``public`` network and return the ipv4
    address
    """
    try:
        return vm.nics.filter(network__public=True)[0].ipv4
    except IndexError:
        return "No public ip"


VM_STATE_CSS_MAP = {
        'BUILD': 'warning',
        'ERROR': 'important',
        'STOPPED': 'notice',
        'STARTED': 'success',
        'DESTROYED': 'inverse'
}
@register.filter(name="vm_status_badge")
def vm_status_badge(vm):
    """
    Return a span badge styled based on the vm current status
    """
    state_cls = VM_STATE_CSS_MAP[vm.operstate]
    badge_cls = "badge badge-%s" % state_cls

    deleted_badge = ""
    if vm.deleted:
        deleted_badge = '<span class="badge badge-important">Deleted</span>'
    return '%s\n<span class="%s">%s</span>' % (deleted_badge, badge_cls,
            vm.operstate)

vm_status_badge.is_safe = True

@register.filter(name="network_deleted_badge")
def network_deleted_badge(network):
    """
    Return a span badge styled based on the vm current status
    """
    deleted_badge = ""
    if network.state == "DELETED":
        deleted_badge = '<span class="badge badge-important">Deleted</span>'
    return deleted_badge

network_deleted_badge.is_safe = True
