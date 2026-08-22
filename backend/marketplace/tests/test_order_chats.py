from rest_framework.test import APITestCase

from marketplace.marketplace_models import VendorOrder
from marketplace.models import Order, Product, User, VendorProfile
from marketplace.order_chat_models import OrderChat


class OrderChatTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="967700000001", username="967700000001", password="StrongPass123!", role="customer")
        self.vendor_user = User.objects.create_user(phone="967700000002", username="967700000002", password="StrongPass123!", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.vendor_user, store_name="متجر الاختبار", slug="chat-test-vendor", status="active")
        self.order = Order.objects.create(customer=self.customer, order_number="ORD-CHAT-1", total=100, currency="YER")
        self.vendor_order = VendorOrder.objects.create(order=self.order, vendor=self.vendor, order_number="ORD-CHAT-1-1", subtotal=100, total=100, vendor_net=90, currency="YER")

    def test_customer_can_ensure_and_read_vendor_chat(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post("/api/order-chats/ensure_for_order/", {"order_id": self.order.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(OrderChat.objects.count(), 1)

    def test_vendor_can_reply_to_own_order_chat(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post("/api/order-chats/ensure_for_order/", {"order_id": self.order.id}, format="json")
        chat_id = response.data[0]["id"]
        self.client.force_authenticate(self.vendor_user)
        message = self.client.post(f"/api/order-chats/{chat_id}/send_message/", {"body": "مرحبًا، طلبك قيد التجهيز."}, format="json")
        self.assertEqual(message.status_code, 201)
        self.assertEqual(message.data["body"], "مرحبًا، طلبك قيد التجهيز.")

    def test_other_vendor_cannot_access_chat(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post("/api/order-chats/ensure_for_order/", {"order_id": self.order.id}, format="json")
        chat_id = response.data[0]["id"]
        other_user = User.objects.create_user(phone="967700000003", username="967700000003", password="StrongPass123!", role="vendor")
        VendorProfile.objects.create(owner=other_user, store_name="متجر آخر", slug="chat-test-other", status="active")
        self.client.force_authenticate(other_user)
        response = self.client.get(f"/api/order-chats/{chat_id}/")
        self.assertEqual(response.status_code, 404)
