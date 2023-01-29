import shutil
import tempfile
from django import forms
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Post, Group, Follow


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

POST_IN_FIRST_PAGE = 10
POST_IN_SECOND_PAGE = 3


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(author=cls.user,
                                       text='Тестовый текст',
                                       group=cls.group,
                                       image=cls.uploaded)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                    'username': self.user.username}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                    'post_id': self.post.id}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={
                    'post_id': self.post.id}): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом"""
        response = self.guest_client.get(reverse('posts:index'))
        first_post = response.context.get('page_obj')[0]
        self.assertEqual(first_post.id, self.post.id)
        self.assertEqual(first_post.text, self.post.text)
        self.assertEqual(first_post.author.username, self.user.username)
        self.assertEqual(first_post.author.get_full_name(),
                         self.user.get_full_name())

    def test_group_list_show_correct_context(self):
        """Шаблон group сформирован с правильным контекстом"""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        first_post = response.context.get('page_obj')[0]
        self.assertEqual(first_post.id, self.post.id)
        self.assertEqual(first_post.text, self.post.text)
        self.assertEqual(first_post.author, self.post.author)
        self.assertEqual(first_post.group.title, self.group.title)
        self.assertEqual(first_post.group.description, self.group.description)
        self.assertEqual(first_post, self.post)

    def test_post_create_show_correct_context(self):
        """Шаблон new_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_added_correctly_user2(self):
        """Пост при создании не добавляется другому пользователю
           Но виден на главной и в группе"""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        posts_count = Post.objects.filter(group=self.group).count()
        post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user2,
            group=group2)
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        group = Post.objects.filter(group=self.group).count()
        profile = response_profile.context['page_obj']
        self.assertEqual(group, posts_count, 'поста нет в другой группе')
        self.assertNotIn(post, profile,
                         'поста нет в группе другого пользователя')

    def test_posts_cache(self) -> None:
        """
        Проверки, которые проверяют работу кеша главной страницы(index).
        """
        response = self.guest_client.get(reverse('posts:index'))
        content = response.content
        Post.objects.filter(group=self.group).delete()
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(content, response.content)
        cache.clear()
        response = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(content, response.content)

    def test_posts_detail_uses_correct_context_first_page(self) -> None:
        """Проверка изображения в context"""
        response = self.guest_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': 1}))
        self.assertIsNotNone(response.context['post'].image)

    def test_auth_user_can_follow_author(self):
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user2}))
        following = Follow.objects.filter(user=self.user, author=self.user2)
        self.assertTrue(following)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user2}))
        unfollowing = Follow.objects.filter(user=self.user, author=self.user2)
        self.assertFalse(unfollowing)

    def test_followers_can_see_new_posts_of_authors_they_follow(self):
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user2)
        self.authorized_client_2.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user}))
        response = self.authorized_client_2.get(reverse('posts:follow_index'))
        self.assertEqual(len(
            response.context['page_obj']), self.POSTS_ON_FIRST_PAGE)
        self.assertEqual(
            response.context['page_obj'][0].author.username,
            self.user.username)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.guest_client = Client()
        cls.user = get_user_model().objects.create(username='User')
        for i in range(13):
            Post.objects.create(author=cls.user, text=f'Текст{i}')

    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))

        self.assertEqual(len(response.context.get('page_obj').object_list),
                         POST_IN_FIRST_PAGE)

    def test_second_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')

        self.assertEqual(len(response.context.get('page_obj').object_list),
                         POST_IN_SECOND_PAGE)
