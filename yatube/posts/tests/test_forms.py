import shutil
import tempfile

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from http import HTTPStatus
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase, override_settings

from posts.models import Group, Post, Comment
from posts.forms import PostForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тest title',
            description='Test description',
            slug='Test-slyg'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Test text',
            group=cls.group,
            image=cls.uploaded
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def tearDown(self):
        cache.clear()

    def create_helper(self, form_data):
        """Вспомогательная функция для проверки создания поста."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        last_post = Post.objects.latest('pub_date')
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.author.username}
        ))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.author, form_data['author'])

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        form_data = {
            'text': 'Test text 2',
            'author': self.author,
        }
        self.create_helper(form_data)

    def test_create_post_with_group(self):
        """Валидная форма с группой создает запись в Post."""
        form_data = {
            'text': 'Test text 3',
            'author': self.author,
            'group': self.group.id,
        }
        self.create_helper(form_data)
        self.assertEqual(
            Post.objects.latest('pub_date').group.id, form_data.get('group'))

    def test_create_post_with_image(self):
        """Валидная форма с картинкой создаёт запись в Post."""
        form_data = {
            'text': 'Test text 4',
            'author': self.author,
            'group': self.group.id,
            'image': self.uploaded,
        }
        self.create_helper(form_data)
        self.assertTrue(
            Post.objects.filter(
                image='posts/small.gif').exists())

    def test_create_post_guest_user(self):
        """Проверяем что гость не может опубликовать пост"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Test text 5',
            'group': self.group.id,
            'author': self.author,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'users:login') + '?next=' + reverse(
            'posts:post_create'))
        self.assertEqual(Post.objects.count(), posts_count)

    def edit_helper(self, form_data):
        """Вспомогательная функция для проверки редактирования поста."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.id
        }))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(
            get_object_or_404(Post, id=self.post.id).text,
            form_data.get('text')
        )
        self.assertEqual(
            get_object_or_404(Post, id=self.post.id).author,
            form_data.get('author')
        )

    def test_edit_post(self):
        """Изменение поста работает корректно."""
        form_data = {
            'text': 'Test text 6',
            'author': self.author,
        }
        self.edit_helper(form_data)

    def test_edit_post_with_group(self):
        """Изменение поста с группой работает корректно."""
        form_data = {
            'text': 'Test text 7',
            'author': self.author,
            'group': self.group.id
        }
        self.edit_helper(form_data)
        self.assertEqual(
            get_object_or_404(Post, id=self.post.id).group.id,
            form_data.get('group')
        )

    def test_create_comment(self):
        """Валидная форма создает новый коментарий"""
        form_data = {
            'text': 'Text comment',
        }
        comment_count = Comment.objects.count()
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        last_comment = Comment.objects.latest('created')
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.id
        }))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(last_comment.text, form_data['text'])

    def test_create_comment_quest(self):
        """Гость не может создать коментарий"""
        form_data = {
            'text': 'Text comment',
        }
        comment_count = Comment.objects.count()
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.id
        }))
        self.assertEqual(Comment.objects.count(), comment_count)
