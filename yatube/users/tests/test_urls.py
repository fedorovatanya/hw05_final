from django.contrib.auth import get_user_model
from http import HTTPStatus
from django.test import TestCase, Client

User = get_user_model()


class UsersURLTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')

    def setUp(self) -> None:
        # Создаём экземпляр клиента. Он неавторизован.
        self.guest_client = Client()
        # Создаём экземпляр клиента.
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)

    def test_available_user_not_login_page(self):
        """Проверка доступности страницы регистрации и входа"""
        adress_tempalte = {
            '/auth/signup/': HTTPStatus.OK,
            '/auth/login/': HTTPStatus.OK,
        }
        for adress, answer in adress_tempalte.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, answer)

    # Для авторизованных пользователей
    def test_available_signup_page(self):
        """Проверка доступности страницы выхода"""
        response = self.authorized_client.get('/auth/logout/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Проверка HTML шаблонов
    def test_users_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        template_url_names = {
            'users/logged_out.html': '/auth/logout/',
            'users/signup.html': '/auth/signup/',
            'users/login.html': '/auth/login/',
        }
        for template, address in template_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
