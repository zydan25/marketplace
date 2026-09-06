from django.urls import path
from .legacy_views import service_center, provider_setup_v2, distribution_v2

urlpatterns=[
 path("",service_center,name="legacy-services-home"),
 path("main/",service_center,{"section":"main"},name="legacy-services-main"),
 path("categories/",service_center,{"section":"categories"},name="legacy-services-categories"),
 path("services/",service_center,{"section":"services"},name="legacy-services-list"),
 path("fields/",service_center,{"section":"fields"},name="legacy-services-fields"),
 path("resources/",service_center,{"section":"resources"},name="legacy-services-resources"),
 path("providers/",provider_setup_v2,name="legacy-services-providers"),
 path("distribution/",distribution_v2,name="legacy-services-distribution"),
]
