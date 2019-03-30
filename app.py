from flask import Flask, render_template, redirect, request, url_for, send_file, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.wsgi import LimitedStream
# Needed?
from sqlalchemy import or_, and_
import os
import json
from flask_s3 import FlaskS3
import flask_s3
import boto3
import random
import string

app = Flask(__name__)
# SQL-Alchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recipeapp.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dsaf0897sfdg45sfdgfdsaqzdf98sdf0a'
# AWS
app.config['FLASKS3_BUCKET_NAME'] = "recipe-db"
app.config['FLASKS3_ACTIVE'] = False
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

os.environ["CONTENT_LENGTH"] = "24"

s3 = FlaskS3(app)
db = SQLAlchemy(app)

class StreamConsumingMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        stream = LimitedStream(environ['wsgi.input'],
                               int(os.environ['CONTENT_LENGTH'] or 0))
        environ['wsgi.input'] = stream
        app_iter = self.app(environ, start_response)
        try:
            stream.exhaust()
            for event in app_iter:
                yield event
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
                
app.wsgi_app = StreamConsumingMiddleware(app.wsgi_app)

def create_pagination_num(total_pages, page):
    
    pagination_num = []
    for counter, p in enumerate(range(0,total_pages)):
        if len(pagination_num) > 5:
            break
        if total_pages < 6 or page > total_pages - 3:
            for counter, p in enumerate(range(0,5)):
                if total_pages - counter > 0:
    
                    pagination_num.insert(0, total_pages - counter)
            break
        # Added to ensure active number is in middle of pagination where possible
        else:
            if page + counter - 2 > 0 and page + counter - 2 < total_pages:
                pagination_num.append(int(page + counter - 2))
                
    return pagination_num
    
def return_search(filters, search_term, page):
    # Recipe_type is a list of filters a user has selected
    # search_term is the search string a user has inputted
    # page is the current page in the pagination a user is on
    
    # Don't need to check as filters will always be there?
    # if not filters["recipe_type"] and not filters["difficulty_type"]:
    #     checkboxes = [None, None, None]
    #     result = (Recipe.query
    #     .filter(Recipe.name.contains(search_term))
    #     .order_by(Recipe.views.desc())
    #     .paginate(page, 6, False))
    # else:

    filter_list_for_recipe_type = []
    for filter_res in filters["recipe_type"]:
        if filter_res == "gluten-free":
            filter_list_for_recipe_type.append(~Recipe.ingredients.any(Ingredients.is_gluten_free == False))
        if filter_res == "vegan":
            filter_list_for_recipe_type.append(~Recipe.ingredients.any(Ingredients.is_vegan == False))
        if filter_res == "vegetarian":
            filter_list_for_recipe_type.append(~Recipe.ingredients.any(Ingredients.is_vegetarian == False))
            
    ingredients_filter_list = []
    
    filter_list_for_ingredients = []
    if filters["ingredients"]:
        for ingredient in filters["ingredients"]:
            filter_list_for_ingredients.append(Recipe.ingredients.any(Ingredients.name.contains(str(ingredient))))
    else: 
        filter_list_for_ingredients.append(Recipe.ingredients.any(Ingredients.id >= 1))

    checkboxes = ["vegan", "vegetarian", "gluten_free"]
    result = (Recipe.query
    .filter(Recipe.name.contains(search_term))
    .filter(*filter_list_for_recipe_type)
    .filter(*filter_list_for_ingredients)
    .filter(Recipe.difficulty.in_(filters["difficulty_type"]))
    .filter(Recipe.serves >= filters["serves"][0])
    .filter(Recipe.serves <= filters["serves"][1])
    .filter(Recipe.time >= filters["time"][0])
    .filter(Recipe.time <= filters["time"][1])
    .order_by(Recipe.views.desc())
    .paginate(page, 6, False))
    
            
    return result
    
# def remove_search_filters():
#     if request.path != "testing":
#         session.pop("search-term")
#         session.pop("filters")
    
# Assistance for function provided by CI tutor
def save_profile_picture(form_picture):          
    random_hex = ''.join([random.choice(string.digits) for n in range(8)])    
    _, f_ext = os.path.splitext(form_picture.filename)  
    picture_fn = random_hex + f_ext
    s3 = boto3.resource('s3')
    s3.Bucket('recipe-db').put_object(Key="static/recipe_images/" + picture_fn, Body=form_picture)
    
    return picture_fn 

recipe_ingredients = db.Table('recipe_ingredients',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id')),
    db.Column('ingredients_id', db.Integer, db.ForeignKey('ingredients.id')),
)

viewed_recipes = db.Table('viewed_recipes',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id')),
    # Change to user_id when database is updated
    db.Column('user_ud', db.Integer, db.ForeignKey('user.id')),
)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    serves = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(6), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    views = db.Column(db.Integer, nullable=False, default='0')
    method = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.Text, nullable=False)
    ingredients = db.relationship('Ingredients', secondary=recipe_ingredients, lazy='dynamic',
        backref=db.backref('ingredients', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
        nullable=False)    

    def __repr__(self):
        return '<Recipe %r>' % (self.id)
        
class Ingredients(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Removed unique, still need to db.create_all()
    name = db.Column(db.String(80), nullable=False)
    # unit = db.Column(db.String(80), nullable=True)
    amount = db.Column(db.String(80), nullable=False)
    is_vegetarian = db.Column(db.Boolean, nullable=False)
    is_vegan = db.Column(db.Boolean, nullable=False)
    is_gluten_free = db.Column(db.Boolean, nullable=False)
    
    def __repr__(self):
        return '<Ingredients %r>' % self.name
        
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    recipe = db.relationship('Recipe', backref="author", lazy=True)
    viewed_recipe = db.relationship('Recipe', secondary=viewed_recipes, lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.username

@app.route('/auto-search/<filter_to_add>')
def auto_search(filter_to_add):
    
    session["filters"] = {
            'difficulty_type': [u'easy', u'medium', u'hard'], 
            'recipe_type': [filter_to_add], 
            'time': [u'10', u'180'], 
            'serves': [u'1', u'6'], 
            'ingredients': []
        }
        
    session["search_term"] = ""
    
    return redirect(url_for('search_get'))

@app.route('/search', methods=["POST"])
def search_post():
    
    search_term = request.form["search"] 
    session["search_term"] = search_term
    
    page = request.args.get('page', 1, type=int)
    
    # filters
    filters = {}
    # Get form data
    try:
        recipe_type = request.form.getlist('recipe-type')
        difficulty_type = request.form.getlist('difficulty-type')
        serves_value = request.form["serves-value"]
        time_value = request.form["time-value"]
        ingredients_value = request.form["ingredients-value"].lower()
    except KeyError:
        recipe_type = []
        difficulty_type = [u'easy', u'medium', u'hard']
        serves_value = "1,6"
        time_value = "10,180"
        ingredients_value = ""
        
    # Ingredients
    if not ingredients_value:
        filters["ingredients"] = []
    else:
        ingredients_value_list = [ingredients_value][0].split(',')
        filters["ingredients"] = ingredients_value_list
    # Serves
    serves_value_list = [serves_value][0].split(',')
    filters["serves"] = serves_value_list
    
    # Time
    time_value_list = [time_value][0].split(',')
    filters["time"] = time_value_list
    
    # Recipe type and difficulty
    recipe_type_list = []
    difficulty_list = []
    
    for r in recipe_type:
        recipe_type_list.append(r)
    # If there is no recipe_type, session will show as empty
    filters["recipe_type"] = recipe_type_list
    
    for difficulty in difficulty_type:
        difficulty_list.append(difficulty)
    # If there is no recipe_type, session will show as empty
    filters["difficulty_type"] = difficulty_list
    
    # Apply all filters to session
    session["filters"] = filters
    
    # submission_test = request.form["submission-test"]
    # session["submission_test"] = submission_test
    
    return redirect(url_for('search_get'))

# Split into Post/Redirect/Get to remove Confirm Form Submission message
@app.route('/search', methods=["GET"])
def search_get():
    page = request.args.get('page', 1, type=int)
    if "filters" not in session:
        session["filters"] = {
            'difficulty_type': [u'easy', u'medium', u'hard'], 
            'recipe_type': [], 
            'time': [u'10', u'180'], 
            'serves': [u'1', u'6'], 
            'ingredients': []
        }
    if not "search_term" in session:
        session["search_term"] = ""
    search_term = session["search_term"]
    
    result = return_search(session["filters"], session["search_term"], page)
    
    total_pages = result.pages
    pagination_num = create_pagination_num(total_pages, page)
    
    allergies = ['is_gluten_free','is_vegan','is_vegetarian']
    search_recipes = []
    allergy_info = {}
    
    search_recipes_ids = []
    for res in result.items:
      search_recipes_ids.append(res.id)



    for recipe in search_recipes_ids:
        temp_recipe = Recipe.query.filter_by(id=recipe).first()
        search_recipes.append(temp_recipe)
        temp_allergy = {}
        for allergy in allergies:
            allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe, allergy)).fetchall()
            temp_allergy[allergy] = allergy_res[0][0]
        allergy_info[recipe] = temp_allergy
    
    return render_template('search.html', allergy_info=allergy_info, result=result, search_term=search_term, pagination_num=pagination_num, page=page) 
    
@app.route('/search', methods=['POST', 'GET'])
def search():
    
    page = request.args.get('page', 1, type=int)
    
    checkboxes = [None, None, None]
    
    if request.method == "POST":
        search_term = request.form["search"] 
        session["search_term"] = search_term
        
        recipe_type = request.form.getlist('recipe-type')
        session["recipe_type"] = recipe_type
        
        result = return_search(recipe_type, search_term, 1)

        
        total_pages = result.pages
        pagination_num = create_pagination_num(total_pages, page)
        
        allergies = ['is_gluten_free','is_vegan','is_vegetarian']
        search_recipes = []
        allergy_info = {}
        
        search_recipes_ids = []
        for res in result.items:
          search_recipes_ids.append(res.id)
        
        for recipe in search_recipes_ids:
            temp_recipe = Recipe.query.filter_by(id=recipe).first()
            search_recipes.append(temp_recipe)
            temp_allergy = {}
            for allergy in allergies:
                allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe, allergy)).fetchall()
                temp_allergy[allergy] = allergy_res[0][0]
            allergy_info[recipe] = temp_allergy
        

    else:
        result = None
        search_term = None 
        allergy_info = None
        next_url = None
        prev_url = None
        pagination_num = []
    
    
        # test = Recipe.query.filter(~Recipe.ingredients.any(Ingredients.is_vegan == True))
        # Check to see if returned recipes have nutritional requirements

    
    # checkboxes=checkboxes, make session
    return render_template('search.html', allergy_info=allergy_info, result=result, checkboxes=checkboxes, search_term=search_term, pagination_num=pagination_num, page=page)
    
@app.route('/')
def index():
    
    # Dealing with ResultProxy help https://kite.com/python/docs/sqlalchemy.engine.result.ResultProxy
    # Average view count
    total_views = db.engine.execute('SELECT SUM(views), COUNT(views) FROM Recipe WHERE views > 0;')
    view_data = total_views.fetchone()
    average_views = view_data[0] / view_data[1]

    recipe_names = Recipe.query.filter(Recipe.views > average_views).all()
    recipe_dict = {}
    for recipe in recipe_names:
        # recipe_dict.update({recipe.name:recipe.id})
        recipe_dict.update({recipe.name: recipe.id})
    # https://stackoverflow.com/questions/19884900/how-to-pass-dictionary-from-jinja2-using-python-to-javascript
    recipe_object = (json.dumps(recipe_dict)
    .replace(u'<', u'\\u003c')
    .replace(u'>', u'\\u003e')
    .replace(u'&', u'\\u0026')
    .replace(u"'", u'\\u0027'))
    
    # Altering the homepage 
    allergies = ['is_gluten_free','is_vegan','is_vegetarian']
    featured_recipes_ids = [1, 2, 3, 4]
    featured_recipes = []
    allergy_info = {}

    
    # for recipe in featured_recipes_ids:
    #     temp_recipe = Recipe.query.filter_by(id=recipe).first()
    #     featured_recipes.append(temp_recipe)
        
        
    #     temp_allergy = {}
    #     for allergy in allergies:
    #         allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe, allergy)).fetchall()
    #         temp_allergy[allergy] = allergy_res[0][0]
    #     allergy_info[recipe] = temp_allergy

    featured_recipes = Recipe.query.order_by(Recipe.views.desc()).limit(4).all()

    for recipe in featured_recipes:
        temp_allergy = {}
        for allergy in allergies:
            allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe.id, allergy)).fetchall()
            temp_allergy[allergy] = allergy_res[0][0]
        allergy_info[recipe.id] = temp_allergy
            
    return render_template('index.html',recipe_object=recipe_object, featured_recipes=featured_recipes, allergy_info=allergy_info)
    
@app.route('/delete/<recipe_id>')
def delete_recipe(recipe_id):
    
    if not session:
        return redirect(url_for('index'))
        
    if not 'username' in session:
        return redirect(url_for('index'))
        
    user = User.query.filter_by(username=session["username"]).first()
    
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    
    if user.id != recipe.user_id:
        flash("You may only delete recipes you own")
        return redirect(url_for('account_my_recipes'))
    
    Recipe.query.filter_by(id=recipe_id).delete()
    
    db.session.commit()
    
    delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
    db.engine.execute(delete_str)
    
    flash("Recipe deleted successfully")
    return redirect(url_for('account_my_recipes'))
    
@app.errorhandler(413)
def page_not_found(e):
    return "Your error page for 413 status code", 413
    
@app.route('/add-recipe/info', methods=['POST', 'GET'])
def add_recipe_info():
    
    if not session:
        return redirect(url_for('register'))
        
    if 'username' not in session:
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        
        # Add check to see if recipe name has been added before
        try:
            recipe_picture = request.files['inputFile']
        except RequestEntityTooLarge:
            print("error")
            return redirect(url_for('index'))
        else:
            image_file_url = save_profile_picture(recipe_picture)
        
        session["added_recipe"] = {
            'name': request.form['dish_name'],
            'serves': request.form['serves'],
            'difficulty': request.form['difficulty'],
            'time': request.form['time'],
            'method': request.form['method'],
            'image_file_url': image_file_url
        }
        
        return redirect(url_for('add_recipe_ingredients'))
        
    return render_template('upload.html')

@app.route('/update-recipe/info/<recipe_id>', methods=['POST', 'GET'])
def update_recipe_info(recipe_id):
    
    # Add check to see if session has username
    if not session:
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    if 'username' not in session:
        flash("Please login to update recipes")
        return redirect(url_for('register'))
    
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    user = User.query.filter_by(username=session["username"]).first()
    
    # Check if user.id is same as recipe
    if recipe.user_id != user.id:
        # Change to account with message
        flash("This recipe can only be edited by its author")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        
        try:
            request.files['inputFile']
        except KeyError:
            image_file_url = recipe.image_file
        else:
            recipe_picture = request.files['inputFile']
            image_file_url = save_profile_picture(recipe_picture)
            

        session["update_recipe"] = {
            'name': request.form['dish_name'],
            'serves': request.form['serves'],
            'difficulty': request.form['difficulty'],
            'time': request.form['time'],
            'method': request.form['method'],
            'image_file_url': image_file_url
        }
    
    # If post update values and redirect to ingreds
        
        return redirect(url_for('update_recipe_ingredients', recipe_id=recipe_id))
    
    return render_template('update.html', recipe=recipe)
    
@app.route('/add-recipe/ingredients', methods=['POST', 'GET'])
def add_recipe_ingredients():
    
    if not session:
        return redirect(url_for('register'))
        
    if 'username' not in session:
        return redirect(url_for('register'))
    
    if "added_recipe" not in session:
        return redirect(url_for('add_recipe_info'))
        
    if request.method == "POST":
        
        session["added_recipe_ingredients"] = {}

        for counter, (ingred, amount) in enumerate(zip(request.form.getlist('ingredient'),
                                          request.form.getlist('amount'))):
                
                
                is_vegetarian = False
                is_vegan = False
                is_gluten_free = False
                
                if request.form.getlist('vegetarian-' + str(counter)):
                    is_vegetarian = True

                if request.form.getlist('vegan-' + str(counter)):
                    is_vegan = True
                
                if request.form.getlist('gluten-free-' + str(counter)):
                    is_gluten_free = True
            
                temp_ingred = {
                    "ingred": ingred.lower(),
                    "amount": amount.lower(),
                    "is_vegetarian" : is_vegetarian,
                    "is_vegan" : is_vegan,
                    "is_gluten_free" : is_gluten_free
                }
                session["added_recipe_ingredients"][counter] = temp_ingred
    

        return redirect(url_for('add_recipe_submit'))
    
    # temp_recipe = Recipe(name=name,image_file=image_file_url,serves = serves,difficulty=difficulty,time=time,views = 0,method = method,user_id = 1)
    # db.session.add(temp_recipe)
    # db.session.commit()
    

    
    return render_template('upload_ingred.html')

@app.route('/update-recipe/ingredients/<recipe_id>', methods=['POST', 'GET'])  
def update_recipe_ingredients(recipe_id):
    
    if not session:
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    if 'username' not in session:
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    if "update_recipe" not in session:
        return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
    
    user = User.query.filter_by(username=session["username"]).first()
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    # Check if user.id is same as recipe
    if recipe.user_id != user.id:
        # Change to account with message
        flash("This recipe can only be edited by its author")
        return redirect(url_for('index'))
    
    search_str = "SELECT * FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
    all_ingreds_id = db.engine.execute(search_str).fetchall()
    
    all_ingreds = {}
    for counter, (k, v) in enumerate(all_ingreds_id):

        all_ingreds[counter] = Ingredients.query.filter_by(id=v).first()
    
    if request.method == "POST":
        
        session["update_recipe_ingredients"] = {}

        for counter, (ingred, amount) in enumerate(zip(request.form.getlist('ingredient'),
                                          request.form.getlist('amount'))):
                
                is_vegetarian = False
                is_vegan = False
                is_gluten_free = False
                
                if request.form.getlist('vegetarian-' + str(counter)):
                    is_vegetarian = True

                if request.form.getlist('vegan-' + str(counter)):
                    is_vegan = True
                
                if request.form.getlist('gluten-free-' + str(counter)):
                    is_gluten_free = True
            
                temp_ingred = {
                    "ingred": ingred,
                    "amount": amount,
                    "is_vegetarian" : is_vegetarian,
                    "is_vegan" : is_vegan,
                    "is_gluten_free" : is_gluten_free
                }
                session["update_recipe_ingredients"][counter] = temp_ingred
    
        return redirect(url_for('update_recipe_submit', recipe_id=recipe_id))
    
    # temp_recipe = Recipe(name=name,image_file=image_file_url,serves = serves,difficulty=difficulty,time=time,views = 0,method = method,user_id = 1)
    # db.session.add(temp_recipe)
    # db.session.commit()
    
    return render_template('update_ingred.html', all_ingreds=all_ingreds, recipe_id=recipe_id)

@app.route('/add-recipe/submit', methods=['POST', 'GET'])
def add_recipe_submit():
    
    if not session:
        return redirect(url_for('register'))
        
    if 'username' not in session:
        return redirect(url_for('register'))
    
    # Why is this not working?    
    try:
        session["added_recipe_ingredients"]
    except KeyError:
        redirect(url_for('add_recipe_info'))
    
    user = User.query.filter_by(username=session["username"]).first()
    added_recipe_ingredients = session["added_recipe_ingredients"]
    added_recipe = session["added_recipe"]
    
    temp_recipe = Recipe(name=session["added_recipe"]["name"],
                        image_file=session["added_recipe"]["image_file_url"],
                        serves = session["added_recipe"]["serves"],
                        difficulty=session["added_recipe"]["difficulty"],
                        time=session["added_recipe"]["time"],
                        views = 0,
                        method = session["added_recipe"]["method"],
                        user_id = user.id)
                        
    db.session.add(temp_recipe)
    
    allergy_info = {
        'is_vegan': True,
        'is_vegetarian': True,
        'is_gluten_free': True
    }
    
    for k, v in session["added_recipe_ingredients"].items():
        for allergy in allergy_info:
            if v[allergy] == False:
                allergy_info[allergy] = False
    
    for counter, (k, v) in enumerate(session["added_recipe_ingredients"].items()):
        
        # Add check to see if ingredient, unit, amount has been added before, if so skip adding it and append from db
        
        ingreds = Ingredients(name=v["ingred"],
                              is_vegetarian = v["is_vegetarian"],
                              is_vegan=v["is_vegan"],
                              is_gluten_free=v["is_gluten_free"],
                              amount=v["amount"])
                              
        
        
        db.session.add(ingreds)
        temp_recipe.ingredients.append(ingreds)
    

    if request.method == "POST":
        
        session.pop("added_recipe")
        session.pop("added_recipe_ingredients")
        db.session.commit()
        
        
        flash("Recipe added successfully")
        return redirect(url_for('account_my_recipes'))
        
    
    return render_template('upload_submit.html', allergy_info=allergy_info, added_recipe=added_recipe, added_recipe_ingredients=added_recipe_ingredients)
    
# Change to update-recipe
@app.route('/update_recipe/submit/<recipe_id>', methods=['POST', 'GET'])
def update_recipe_submit(recipe_id):
    
    if not session:
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    if 'username' not in session:
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    if "update_recipe" not in session:
        return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
        
    if "update_recipe_ingredients" not in session:
        return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
        
        
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    user = User.query.filter_by(username=session["username"]).first()
    
    # Check if user.id is same as recipe
    if recipe.user_id != user.id:
        # Change to account with message
        flash("This recipe can only be edited by its author")
        return redirect(url_for('index'))
    
    update_recipe_ingredients = session["update_recipe_ingredients"]
    update_recipe = session["update_recipe"]
                        
    allergy_info = {
        'is_vegan': True,
        'is_vegetarian': True,
        'is_gluten_free': True
    }
    
    view_count = Recipe.query.filter_by(id=recipe_id).with_entities(Recipe.views).first()
    view_count = view_count[0]

    for k, v in session["update_recipe_ingredients"].items():
        for allergy in allergy_info:
            if v[allergy] == False:
                allergy_info[allergy] = False
     
    if request.method == "POST":
        
        temp_recipe = Recipe.query.filter_by(id=recipe_id).first()
        temp_recipe.name = session["update_recipe"]["name"]
        temp_recipe.image_file = session["update_recipe"]["image_file_url"]
        temp_recipe.serves = session["update_recipe"]["serves"]
        temp_recipe.difficulty=session["update_recipe"]["difficulty"]
        temp_recipe.time=session["update_recipe"]["time"]
        temp_recipe.method = session["update_recipe"]["method"]
        
        delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
        db.engine.execute(delete_str)
        
        db.session.commit()
        
        for counter, (k, v) in enumerate(session["update_recipe_ingredients"].items()):
        
        # Add check to see if ingredient, unit, amount has been added before, if so skip adding it and append from db
        
            ingreds = Ingredients(name=v["ingred"],
                              is_vegetarian = v["is_vegetarian"],
                              is_vegan=v["is_vegan"],
                              is_gluten_free=v["is_gluten_free"],
                              amount=v["amount"])
                              
            db.session.add(ingreds)
            temp_recipe.ingredients.append(ingreds)
        
        db.session.commit()
        
        
        session.pop("update_recipe")
        session.pop("update_recipe_ingredients")
        
        flash("Recipe updated successfully")
        return redirect(url_for('account_my_recipes'))
    
    
    return render_template('update_submit.html', view_count=view_count, recipe_id=recipe_id, allergy_info=allergy_info, update_recipe=update_recipe, update_recipe_ingredients=update_recipe_ingredients)
    
@app.route('/recipe/<recipe_name>/<recipe_id>')
def recipe(recipe_name, recipe_id):

    recipe_result = Recipe.query.filter_by(id=recipe_id).first()
    ingredients_result = recipe_result.ingredients.all()
    user = []
    # Will need to change to try
    if "username" in session:

        user = User.query.filter_by(username=session["username"]).first()
        
        # Change to user_id when database is updated
        search_str = "SELECT * FROM viewed_recipes WHERE user_ud = %s AND recipe_id = %s ;" % (user.id, recipe_id)
        viewed_recipe = db.engine.execute(search_str).fetchall()
        
        if not viewed_recipe:
            user.viewed_recipe.append(recipe_result)
            recipe_result.views = recipe_result.views + 1
            db.session.commit()

            """
            A test account with a permenant not-viewed state necessary for
            multiple tests in app_test.py
            """
            # if session["username"] == "testing-account-not-viewed-recipe":
            #     db.engine.execute('DELETE FROM viewed_recipes WHERE user_ud = 55')
            #     recipe_result.views = recipe_result.views - 1
            #     db.session.commit()
            #     print(recipe_result.views)
            
    allergies = ['is_gluten_free','is_vegan','is_vegetarian']
    allergy_info = {}
    
    temp_allergy = {}
    for allergy in allergies:
        # Change to FALSE for Heroku
        allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe_result.id, allergy)).fetchall()
        allergy_info[allergy] = allergy_res[0][0]
    
    filter_words = ["and", "with", "recipe", "on", "the", "&", "side", "of"]
    recipe_result_name_list = (x for x in recipe_result.name.split(' ') if not x in filter_words)
    
    
    related_recipe_result = []
    
    for word in recipe_result_name_list:
        temp_related = Recipe.query.filter(Recipe.name.like("%" + word + "%")).filter(Recipe.id != recipe_result.id)
        for temp_result in temp_related:
            if len(related_recipe_result) > 2:
                break
            if not temp_related in related_recipe_result:
                # Does this if work?
                related_recipe_result.append(temp_result)
    
    related_allergy_info = {}
    for counter, recipe in enumerate(related_recipe_result):  
        related_allergy_info[str(recipe.id)] = {}
        for allergy in allergies:
            allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe.id, allergy)).fetchall()
            id_num = "id_" + str(recipe.id)
            related_allergy_info[str(recipe.id)][allergy] = allergy_res[0][0]
    
    
    # related_recipes = []
    # while related_recipes > 3:
    

    return render_template('recipe.html', user=user, related_recipe_result=related_recipe_result, related_allergy_info=related_allergy_info, recipe_result=recipe_result, ingredients_result=ingredients_result, allergy_info=allergy_info)
    
@app.route('/account/my-recipes', methods=['POST', 'GET'])
def account_my_recipes():
    
    if not session:
        return redirect(url_for('register'))
        
    if 'username' not in session:
        return redirect(url_for('register'))
    
    user = User.query.filter_by(username=session['username']).first()
    all_recipes = Recipe.query.filter_by(user_id=user.id).with_entities(Recipe.name, Recipe.id).order_by(Recipe.views.desc()).all()
    
    if request.method == "POST":
        if user.password == request.form["current-password"]:
        
            temp_user = User.query.filter_by(id=user.id).first()
            if 'first_name' in request.form:
                temp_user.first_name = request.form['first_name']
            if 'last_name' in request.form:
                temp_user.last_name = request.form["last_name"]
            if 'username' in request.form:
                temp_user.username = request.form["username"]
                session['username'] = request.form["username"]
            if 'password' in request.form:
                temp_user.password = request.form["password"]
            
            db.session.commit()
        
        else:
            flash("Password incorrect")
    
    return render_template('account_my_recipes.html', all_recipes=all_recipes, user=user)
    
@app.route('/register', methods=['POST', 'GET'])
def register():
    

    return render_template('register.html')
    
@app.route('/register_user', methods=['POST', 'GET'])
def register_user():
    
    first_name = request.form["first_name"].lower()
    last_name = request.form["last_name"].lower() 
    username = request.form["username"].lower()
    password = request.form["password"].lower()
    

    if User.query.filter_by(username=username).count() > 0:
        return redirect(url_for('register'))
    else:
        session["username"] = username
        
        user = User(first_name=first_name,last_name=last_name, username=username,password = password)
        db.session.add(user)
        db.session.commit()
        
        flash("User registration successful")
        return redirect(url_for('index'))
    return redirect(url_for('register'))
    
@app.route('/login', methods=['POST', 'GET'])
def login():
    
    return render_template('login.html')
    
@app.route('/login_user', methods=['POST', 'GET'])
def login_user():
    
    username = request.form["username"].lower()
    password = request.form["password"]
    
    user = User.query.filter_by(username=username).first()
    
    try:
        user.username
    except AttributeError:
        return redirect(url_for('login'))
    
    if str(user.password) == str(password):
        session["username"] = username
        return redirect(url_for('index'))
    else: 
        return redirect(url_for('login'))
        
@app.route('/logout')
def logout():
    
    session.clear()
    flash("Log out successful")
    return redirect(url_for('index'))
    
# Change debug mode
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
            
# add 404 for missing queries http://flask-sqlalchemy.pocoo.org/2.3/queries/#queries-in-views