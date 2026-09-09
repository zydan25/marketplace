from django.shortcuts import render

from .dashboard import dashboard_access_required, _dashboard_context


ACCOUNTING_SIDEBAR_LINK = (
    '<div class="section-title">المالية</div>'
    '<nav class="nav">'
    '<a href="/admin/dashboard/accounting/" onclick="closeMenu()">'
    '<span>المحاسبة</span><span>▣</span>'
    '</a>'
    '</nav>'
)

SERVICES_SETTINGS_SIDEBAR_LINK = (
    '<div class="section-title">الخدمات</div>'
    '<nav class="nav">'
    '<a href="/admin/dashboard/services/" onclick="closeMenu()">'
    '<span>مركز الخدمات</span><span>NEW</span>'
    '</a>'
    '<a href="/admin/dashboard/services/settings/" onclick="closeMenu()">'
    '<span>إعدادات الخدمات</span><span>⚙</span>'
    '</a>'
    '</nav>'
)


@dashboard_access_required
def dashboard_v2(request):
    response = render(request, "admin/dashboard_v2.html", _dashboard_context())
    html = response.content.decode("utf-8")
    marker = "</aside>"
    if SERVICES_SETTINGS_SIDEBAR_LINK not in html and marker in html:
        html = html.replace(marker, f"{SERVICES_SETTINGS_SIDEBAR_LINK}{marker}", 1)
    if ACCOUNTING_SIDEBAR_LINK not in html and marker in html:
        html = html.replace(marker, f"{ACCOUNTING_SIDEBAR_LINK}{marker}", 1)
    response.content = html.encode("utf-8")
    return response
