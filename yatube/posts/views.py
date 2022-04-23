from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings

from .forms import PostForm, CommentForm
from .models import Group, Post, Comment, Follow


def get_page_context(queryset, request):
    paginator = Paginator(queryset, settings.PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {
        'paginator': paginator,
        'page_number': page_number,
        'page_obj': page_obj,
    }


def index(request):
    template = 'posts/index.html'
    context = get_page_context(Post.objects.all(), request)
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    context = {
        'group': group,
        'post_list': post_list,
    }
    context.update(get_page_context(post_list, request))
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = Post.objects.select_related('author').filter(author=author)
    page_obj = paginate(posts, request)
    posts_count = posts.count()
    user = request.user
    if user.is_authenticated and user != author:
        following = Follow.objects.filter(
            user=user, author=author
        ).exists()
    else:
        following = False
    context = {
        'author': author,
        'page_obj': page_obj,
        'posts_count': posts_count,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    comment_form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=post)
    post_count = author.posts.count()
    # Здесь код запроса к модели и создание словаря контекста
    context = {
        'author': author,
        'post': post,
        'post_count': post_count,
        'form': comment_form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', post.author)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


def paginate(posts, request):
    paginator = Paginator(posts, settings.PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    user = request.user
    posts = Post.objects.filter(author__following__user=user)
    page_obj = paginate(posts, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if user != author and not now_follower:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(user=user, author=author)
    if follow.exists():
        follow.delete()
    return redirect('posts:profile', username=username)
