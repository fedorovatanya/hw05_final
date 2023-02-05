from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from http import HTTPStatus
from ..models import Post, Group


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.user_2 = User.objects.create_user(username='TestUser2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Группа для тестирования'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Пост для проверки',
            group=cls.group
        )
        cls.post_2 = Post.objects.create(
            text='Пост для проверки №2',
            author=cls.user_2,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template_for_guest_user(self):
        """Проверка доступности pages for unauth_users."""
        templates_pages_names = {
            '/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for reverse_name, status in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, status)

    def test_urls_uses_correct_template_for_authorized(self):
        """Проверка доступности страниц для авторизированного пользователя."""
        templates_pages_names = {
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            '/follow/': HTTPStatus.OK,
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, template)

    def test_redirect_post_create_unauth(self) -> None:
        """Проверяем редирект страницы создания поста для гостя"""
        response = self.guest_client.get(reverse(
            'posts:post_create'),
            follow=True)
        self.assertRedirects(
            response, reverse('users:login') + '?next=/create/')

    def test_posts_urls_uses_correct_template(self) -> None:
        """URL-адрес использует соответствующий шаблон."""
        template_url_names = {
            '/': 'posts/index.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            '/follow/': 'posts/follow.html',
        }
        for reverse_name, template in template_url_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
