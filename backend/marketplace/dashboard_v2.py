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


@dashboard_access_required
def dashboard_v2(request):
    response = render(request, "admin/dashboard_v2.html", _dashboard_context())
    marker = "</aside>"
    if ACCOUNTING_SIDEBAR_LINK not in response.content.decode("utf-8") and marker in response.content.decode("utf-8"):
        html = response.content.decode("utf-8").replace(marker, f"{ACCOUNTING_SIDEBAR_LINK}{marker}", 1)
        response.content = html.encode("utf-8")
    return response
