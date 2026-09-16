from django.shortcuts import render

from .dashboard import dashboard_access_required, _dashboard_context


NEW_ERP_DASHBOARD_LINK = (
    '<div class="section-title">واجهة الإدارة</div>'
    '<nav class="nav">'
    '<a href="/admin/dashboard/control/" onclick="closeMenu()">'
    '<span>لوحة الإدارة الجديدة</span><span>NEW</span>'
    '</a>'
    '</nav>'
)

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
    '<a href="/admin/dashboard/services/v2/" onclick="closeMenu()">'
    '<span>منصة الخدمات الجديدة</span><span>V2</span>'
    '</a>'
    '<a href="/admin/dashboard/services/v2/settings/" onclick="closeMenu()">'
    '<span>إعدادات الخدمات</span><span>⚙</span>'
    '</a>'
    '<a href="/admin/dashboard/services/v2/docs/" onclick="closeMenu()">'
    '<span>طريقة الربط</span><span>API</span>'
    '</a>'
    '</nav>'
)


@dashboard_access_required
def dashboard_v2(request):
    response = render(request, "admin/dashboard_v2.html", _dashboard_context())
    html = response.content.decode("utf-8")
    marker = "</aside>"
    for sidebar_link in (NEW_ERP_DASHBOARD_LINK, SERVICES_SETTINGS_SIDEBAR_LINK, ACCOUNTING_SIDEBAR_LINK):
        if sidebar_link not in html and marker in html:
            html = html.replace(marker, f"{sidebar_link}{marker}", 1)
    response.content = html.encode("utf-8")
    return response
