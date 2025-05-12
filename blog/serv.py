from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Загрузка данных из файла
def load_data():
    if not os.path.exists('data.json'):
        return {"users": [], "posts": [], "comments": []}
    with open('data.json', 'r') as f:
        import json
        return json.load(f)


# Сохранение данных в файл
def save_data(data):
    with open('data.json', 'w') as f:
        import json
        json.dump(data, f, indent=4)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Главная страница
@app.route('/')
def home():
    username = session.get('username')
    return render_template('home.html', username=username)


# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Заполните все поля", "error")
            return redirect(url_for('register'))

        data = load_data()
        if any(user['username'] == username for user in data['users']):
            flash("Пользователь с таким именем уже существует", "error")
            return redirect(url_for('register'))

        new_user = {
            "id": max([user['id'] for user in data['users']], default=0) + 1,
            "username": username,
            "password_hash": generate_password_hash(password)
        }
        data['users'].append(new_user)
        save_data(data)
        flash("Регистрация успешна. Теперь вы можете войти.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# Авторизация пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Заполните все поля", "error")
            return redirect(url_for('login'))

        data = load_data()
        user = next((u for u in data['users'] if u['username'] == username), None)
        if not user or not check_password_hash(user['password_hash'], password):
            flash("Неверное имя пользователя или пароль", "error")
            return redirect(url_for('login'))

        session['username'] = username
        flash("Вы успешно вошли", "success")
        return redirect(url_for('home'))

    return render_template('login.html')


# Выход из системы
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Вы успешно вышли из системы", "success")
    return redirect(url_for('home'))


# Список постов
@app.route('/posts')
def view_posts():
    data = load_data()
    posts = data['posts']
    users = {user['id']: user['username'] for user in data['users']}

    posts_with_usernames = [
        {
            "id": post["id"],
            "username": users.get(post["user_id"], "Неизвестный"),
            "title": post["title"],
            "content": post["content"],
            "theme": post.get("theme", "Без темы"),
            "image_url": post.get("image_url", None),
            "tags": post.get("tags", []),
            "created_at": post.get("created_at", "Неизвестно"),
            "likes": post.get("likes", []),
            "dislikes": post.get("dislikes", [])
        }
        for post in posts
    ]

    username = session.get('username')
    return render_template('posts.html', posts=posts_with_usernames, username=username)


# Детальный просмотр поста
@app.route('/posts/<int:post_id>')
def view_post(post_id):
    data = load_data()
    post = next((p for p in data['posts'] if p['id'] == post_id), None)
    if not post:
        abort(404, description="Пост не найден")

    users = {user['id']: user['username'] for user in data['users']}
    comments = data['comments']

    post_with_username = {
        "id": post["id"],
        "username": users.get(post["user_id"], "Неизвестный"),
        "title": post["title"],
        "content": post["content"],
        "theme": post.get("theme", "Без темы"),
        "image_url": post.get("image_url", None),
        "tags": post.get("tags", []),
        "created_at": post.get("created_at", "Неизвестно"),
        "likes": post.get("likes", []),
        "dislikes": post.get("dislikes", [])
    }

    username = session.get('username')
    return render_template(
        'post_detail.html',
        post=post_with_username,
        comments=comments,
        users=users,
        username=username
    )


# Создать пост
@app.route('/posts/create', methods=['GET', 'POST'])
def create_post():
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        theme = request.form.get('theme')
        title = request.form.get('title')
        content = request.form.get('content')
        image = request.files.get('image')  # Получаем файл изображения
        tags_input = request.form.get('tags')
        tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []

        if not theme or not title or not content:
            flash("Заполните все поля", "error")
            return redirect(url_for('create_post'))

        data = load_data()
        user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
        if not user_id:
            flash("Ошибка при создании поста", "error")
            return redirect(url_for('create_post'))

        image_url = None
        if image and image.filename:  # Проверяем, что файл был загружен
            # Сохраняем файл в папку uploads
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            image.save(image_path)
            # Формируем URL для доступа к изображению
            image_url = f"/uploads/{image.filename}"

        new_post = {
            "id": max([p['id'] for p in data['posts']], default=0) + 1,
            "user_id": user_id,
            "theme": theme,
            "title": title,
            "content": content,
            "image_url": image_url,  # Добавляем URL изображения
            "tags": tags,
            "created_at": datetime.now().strftime("%H:%M %d.%m.%Y"),
            "likes": [],
            "dislikes": []
        }
        data['posts'].append(new_post)
        save_data(data)
        flash("Пост успешно создан", "success")
        return redirect(url_for('view_posts'))

    return render_template('create_post.html', username=username)


# Редактирование поста
@app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('login'))

    data = load_data()
    post = next((p for p in data['posts'] if p['id'] == post_id), None)
    if not post:
        abort(404, description="Пост не найден")

    user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
    if post['user_id'] != user_id:
        flash("У вас нет прав для редактирования этого поста", "error")
        return redirect(url_for('view_posts'))

    if request.method == 'POST':
        theme = request.form.get('theme')
        title = request.form.get('title')
        content = request.form.get('content')
        tags_input = request.form.get('tags')
        tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []

        if not theme or not title or not content:
            flash("Заполните все поля", "error")
            return redirect(url_for('edit_post', post_id=post_id))

        post['theme'] = theme
        post['title'] = title
        post['content'] = content
        post['tags'] = tags
        save_data(data)
        flash("Пост успешно обновлен", "success")
        return redirect(url_for('view_posts'))

    return render_template('edit_post.html', post=post, username=username)


# Удаление поста
@app.route('/posts/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('login'))

    data = load_data()
    post = next((p for p in data['posts'] if p['id'] == post_id), None)
    if not post:
        abort(404, description="Пост не найден")

    user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
    if post['user_id'] != user_id:
        flash("У вас нет прав для удаления этого поста", "error")
        return redirect(url_for('view_posts'))

    data['posts'] = [p for p in data['posts'] if p['id'] != post_id]
    save_data(data)
    flash("Пост успешно удален", "success")
    return redirect(url_for('view_posts'))


# Лайк поста
@app.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('view_posts'))

    data = load_data()
    post = next((p for p in data['posts'] if p['id'] == post_id), None)
    if not post:
        abort(404, description="Пост не найден")

    user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
    likes = post.setdefault("likes", [])
    dislikes = post.setdefault("dislikes", [])

    if user_id in likes:
        likes.remove(user_id)
    elif user_id in dislikes:
        dislikes.remove(user_id)
        likes.append(user_id)
    else:
        likes.append(user_id)

    save_data(data)
    return redirect(url_for('view_post', post_id=post_id))


# Дизлайк поста
@app.route('/posts/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('view_posts'))

    data = load_data()
    post = next((p for p in data['posts'] if p['id'] == post_id), None)
    if not post:
        abort(404, description="Пост не найден")

    user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
    likes = post.setdefault("likes", [])
    dislikes = post.setdefault("dislikes", [])

    if user_id in dislikes:
        dislikes.remove(user_id)
    elif user_id in likes:
        likes.remove(user_id)
        dislikes.append(user_id)
    else:
        dislikes.append(user_id)

    save_data(data)
    flash("Дизлайк успешно добавлен", "success")
    return redirect(url_for('view_post', post_id=post_id))


# Создать комментарий
@app.route('/posts/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('login'))

    data = load_data()
    text = request.form.get('text')
    if not text:
        flash("Комментарий не может быть пустым", "error")
        return redirect(url_for('view_post', post_id=post_id))

    user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
    if not user_id:
        flash("Ошибка при добавлении комментария", "error")
        return redirect(url_for('view_post', post_id=post_id))

    new_comment = {
        "id": max([c['id'] for c in data['comments']], default=0) + 1,
        "post_id": post_id,
        "user_id": user_id,
        "text": text,
        "created_at": datetime.now().strftime("%H:%M %d.%m.%Y")
    }
    data['comments'].append(new_comment)
    save_data(data)
    flash("Комментарий успешно добавлен", "success")
    return redirect(url_for('view_post', post_id=post_id))


# Удалить комментарий
@app.route('/comments/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    username = session.get('username')
    if not username:
        flash("Вы не авторизованы", "error")
        return redirect(url_for('login'))

    data = load_data()
    comment = next((c for c in data['comments'] if c['id'] == comment_id), None)
    if not comment:
        abort(404, description="Комментарий не найден")

    user_id = next((user['id'] for user in data['users'] if user['username'] == username), None)
    if comment['user_id'] != user_id:
        flash("У вас нет прав для удаления этого комментария", "error")
        return redirect(url_for('view_post', post_id=comment['post_id']))

    data['comments'] = [c for c in data['comments'] if c['id'] != comment_id]
    save_data(data)
    flash("Комментарий успешно удален", "success")
    return redirect(url_for('view_post', post_id=comment['post_id']))


# Поиск постов
@app.route('/search', methods=['GET'])
def search_posts():
    query = request.args.get('q', '').lower()
    filter_by = request.args.get('filter', 'all')
    if not query:
        return render_template('search.html', results=[], username=session.get('username'))

    data = load_data()
    posts = data['posts']
    users = {user['id']: user['username'] for user in data['users']}
    comments = data['comments']

    filtered_posts = [
        {
            "id": post["id"],
            "username": users.get(post["user_id"], "Неизвестный"),
            "title": post["title"],
            "content": post["content"],
            "theme": post.get("theme", "Без темы"),
            "image_url": post.get("image_url", None),
            "tags": post.get("tags", []),
            "created_at": post.get("created_at", "Неизвестно")
        }
        for post in posts
        if (
                (filter_by == "all" and (
                        query in post["title"].lower() or
                        query in post["content"].lower() or
                        query in post.get("theme", "").lower() or
                        query in users.get(post["user_id"], "").lower() or
                        any(query in tag.lower() for tag in post.get("tags", []))
                )) or
                (filter_by == "title" and query in post["title"].lower()) or
                (filter_by == "content" and query in post["content"].lower()) or
                (filter_by == "theme" and query in post.get("theme", "").lower()) or
                (filter_by == "author" and query in users.get(post["user_id"], "").lower())
        )
    ]

    results_with_comments = []
    for post in filtered_posts:
        post_comments = [
            {
                "id": comment["id"],
                "text": comment["text"],
                "username": users.get(comment["user_id"], "Неизвестный"),
                "created_at": comment.get("created_at", "Неизвестно")
            }
            for comment in comments
            if comment["post_id"] == post["id"]
        ]
        post["comments"] = post_comments
        results_with_comments.append(post)

    if not results_with_comments:
        flash("Постов не найдено", "info")

    return render_template('search.html', results=results_with_comments, username=session.get('username'))


if __name__ == '__main__':
    app.run(debug=True)
