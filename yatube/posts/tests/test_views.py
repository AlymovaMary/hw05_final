from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms

from posts.models import Post, Group, Comment, Follow


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа',
            slug='xest-slug',
            description='Тестовое описание',
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
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(PostURLTests.user)

    def test_correct_template(self):
        """Views index, group_list, profile, detail,"""
        """create_post используют соответствующие шаблоны."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            'posts/profile.html': reverse('posts:profile', args=[self.user]),
            'posts/post_detail.html': reverse(
                'posts:post_detail',
                args=[self.post.pk]
            ),
            'posts/create_post.html': reverse('posts:post_create'),
        }
        for template, view_name in templates_pages_names.items():
            with self.subTest(view_name=view_name):
                response = self.authorized_client.get(view_name)
                self.assertTemplateUsed(response, template)

    def test_post_edit_correct_template(self):
        """Views post_edit использует соответствующий шаблон."""
        response = self.author_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.pk}))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_index_group_list_profile_page_show_correct_context(self):
        """Шаблоны index, group_list, profile"""
        """сформированы с правильным контекстом."""
        templates_context = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        }

        for template_context in templates_context:
            with self.subTest(template_context=template_context):
                response = self.authorized_client.get(template_context)
                first_post = response.context['page_obj'][0]
                self.assertEqual(first_post.text, PostURLTests.post.text)
                self.assertEqual(
                    first_post.author.username,
                    PostURLTests.post.author.username
                )
                self.assertEqual(
                    first_post.group.title, PostURLTests.post.group.title
                )
                self.assertEqual(
                    first_post.image, PostURLTests.post.image
                )

    def test_detail_context(self):
        """Шаблон detail сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            args=[self.post.pk]),
        )
        first_post = response.context['post']
        self.assertEqual(first_post.text, PostURLTests.post.text)
        self.assertEqual(
            first_post.author.username,
            PostURLTests.post.author.username
        )
        self.assertEqual(first_post.group.title, PostURLTests.post.group.title)
        self.assertEqual(
            first_post.image, PostURLTests.post.image
        )

    def test_post_edit_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_new_create_appears_on_correct_pages(self):
        """При создании поста он должен появляется на главной странице,
        на странице выбранной группы и в профиле пользователя"""
        exp_pages = [
            reverse('posts:index'),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user.username})
        ]
        for revers in exp_pages:
            with self.subTest(revers=revers):
                response = self.authorized_client.get(revers)
                self.assertIn(self.post, response.context['page_obj'])

    def test_posts_not_contain_in_wrong_group(self):
        """При создании поста он не появляется в другой группе"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group2.slug})
        )
        self.assertNotIn(
            Post.objects.first(),
            response.context['page_obj'].object_list
        )

    def test_post_edit_random_user(self):
        """Проверка страницы редактирования поста  авторизованным
        пользователем, но не автором"""
        response_random = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}))
        create_context = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in create_context.items():
            with self.subTest(value=value):
                fields = response_random.context.get('form').fields.get(value)
                self.assertIsInstance(fields, expected)

    def test_post_detail_content_comments(self):
        """Шаблон post_detail сожержит комментарии к посту"""
        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Text comment',
        )
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        comment = [response.context.get('comments')][0]
        comment_fields = [{
            'post': self.post,
            'author': self.user,
            'text': self.comment.text,
        }]
        for i in range(len(comment)):
            post_fields = comment_fields[i]
            for value, expected in post_fields.items():
                with self.subTest(post_and_field=f'{i} and {value}'):
                    post_field = getattr(comment[i], value)
                    self.assertEqual(post_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
        )

        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.user,
                group=cls.group))
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_records(self):
        """Проверка работы паджинатора,"""
        """на первой странице отображается 10 постов"""
        urls_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})}
        for test_url in urls_names:
            response = self.authorized_client.get(test_url)
            self.assertEqual(len(response.context['page_obj']), settings.PAGE)

    def test_first_page_contains_three_records(self):
        """Проверка работы паджинатора,"""
        """на второй странице отображается остаток постов - 3 поста"""
        urls_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        }
        count_posts = Post.objects.count()
        remainder_posts = count_posts - settings.PAGE
        for test_url in urls_names:
            response = self.authorized_client.get(test_url + '?page=2')
            self.assertEqual(len(
                response.context['page_obj']),
                remainder_posts
            )


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='just_user')
        cls.user_author = User.objects.create_user(username='author')

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_profile_follow(self):
        """Авторизованный пользователь может подписаться на автора."""
        pre_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertFalse(pre_follower)
        self.authorized_client.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user_author}
        ))
        after_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertTrue(after_follower)

    def test_profile_unfollow(self):
        """Авторизованный пользователь может отписаться от автора."""
        Follow.objects.create(user=self.user, author=self.user_author)
        pre_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertTrue(pre_follower)
        self.authorized_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user_author}
        ))
        after_follower = Follow.objects.filter(
            user=self.user, author=self.user_author
        ).exists()
        self.assertFalse(after_follower)

    def test_non_follow_index(self):
        """При создании автором новой записи,"""
        """она не появляется у не подписчика."""
        Follow.objects.create(user=self.user, author=self.user_author)
        self.new_post = Post.objects.create(
            text='post fo followers',
            author=self.user_author
        )
        self.user_non_follower = User.objects.create_user(
            username='non_follower'
        )
        self.authorized_non_follower = Client()
        self.authorized_non_follower.force_login(self.user_non_follower)
        response_non_follower = self.authorized_non_follower.get(reverse(
            'posts:follow_index'
        ))
        self.assertFalse(self.new_post in response_non_follower.context[
            'page_obj']
        )

    def test_follow_index(self):
        """При создании автором новой записи, она появляется у подписчика."""
        Follow.objects.create(user=self.user, author=self.user_author)
        self.new_post = Post.objects.create(
            text='post fo followers',
            author=self.user_author
        )
        response_follower = self.authorized_client.get(reverse(
            'posts:follow_index'))
        self.assertTrue(self.new_post in response_follower.context['page_obj'])
