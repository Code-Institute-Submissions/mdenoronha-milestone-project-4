from flask import Flask, render_template, redirect, request, url_for, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
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

s3 = FlaskS3(app)
db = SQLAlchemy(app)

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
            filter_list_for_ingredients.append(Recipe.ingredients.any(Ingredients.name == str(ingredient)))
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
    unit = db.Column(db.String(80), nullable=True)
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
    
    print(pagination_num)
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
        next_url = url_for('search', page=result.next_num) \
        if result.has_next else None
        prev_url = url_for('search', page=result.prev_num) \
        if result.has_prev else None
        
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
    return render_template('search.html', allergy_info=allergy_info, result=result, checkboxes=checkboxes, search_term=search_term, next_url=next_url, prev_url=prev_url, pagination_num=pagination_num, page=page)
    
app.route('/mockdata')
def mockdata_url():
    return render_template('register.html')

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
        recipe_dict.update({recipe.name:""})
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

    
    for recipe in featured_recipes_ids:
        temp_recipe = Recipe.query.filter_by(id=recipe).first()
        featured_recipes.append(temp_recipe)
        temp_allergy = {}
        for allergy in allergies:
            allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe, allergy)).fetchall()
            temp_allergy[allergy] = allergy_res[0][0]
        allergy_info[recipe] = temp_allergy



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
        return redirect(url_for('account_my_recipes'))
    
    Recipe.query.filter_by(id=recipe_id).delete()
    
    db.session.commit()
    
    delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
    db.engine.execute(delete_str)

    return redirect(url_for('account_my_recipes'))
    
@app.route('/add-recipe/info', methods=['POST', 'GET'])
def add_recipe_info():
    
    if not session:
        return redirect(url_for('register'))
        
    if 'username' not in session:
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        
        # Add check to see if recipe name has been added before
        
        recipe_picture = request.files['inputFile']
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
    
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    user = User.query.filter_by(username=session["username"]).first()
    
    # Check if user.id is same as recipe
    if recipe.user_id != user.id:
        # Change to account with message
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
    
    # Why is this not working?    
    try:
        session["added_recipe"]
    except KeyError:
        redirect(url_for('add_recipe_info'))
    
    if request.method == "POST":
        
        session["added_recipe_ingredients"] = {}

        for counter, (ingred, amount, unit) in enumerate(zip(request.form.getlist('ingredient'),
                                          request.form.getlist('amount'),
                                          request.form.getlist('unit'))):
                
                
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
                    "unit": unit.lower(),
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
    
    user = User.query.filter_by(username=session["username"]).first()
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    # Check if user.id is same as recipe
    if recipe.user_id != user.id:
        # Change to account with message
        return redirect(url_for('index'))
    
    search_str = "SELECT * FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
    all_ingreds_id = db.engine.execute(search_str).fetchall()
    
    all_ingreds = {}
    for counter, (k, v) in enumerate(all_ingreds_id):

        all_ingreds[counter] = Ingredients.query.filter_by(id=v).first()
        
        # Why is this not working? 
    # Add check to see update recipe is same as recipe_id
    try:
        session["update_recipe"]
    except KeyError:
        redirect(url_for('update_recipe_info', recipe_id=recipe_id))
    
    if request.method == "POST":
        
        session["update_recipe_ingredients"] = {}

        for counter, (ingred, amount, unit) in enumerate(zip(request.form.getlist('ingredient'),
                                          request.form.getlist('amount'),
                                          request.form.getlist('unit'))):
                
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
                    "unit": unit,
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
                              unit=v["unit"],
                              amount=v["amount"])
                              
        
        
        db.session.add(ingreds)
        temp_recipe.ingredients.append(ingreds)
    
    if request.method == "POST":
        
        session.pop("added_recipe")
        session.pop("added_recipe_ingredients")
        db.session.commit()
        
        
        
        return redirect(url_for('account_my_recipes'))
        
    
    return render_template('upload_submit.html', allergy_info=allergy_info, added_recipe=added_recipe, added_recipe_ingredients=added_recipe_ingredients)
    
@app.route('/update_recipe/submit/<recipe_id>', methods=['POST', 'GET'])
def update_recipe_submit(recipe_id):
    # Checks to see if this is their recipes
        # Why is this not working?    
    try:
        session["added_recipe_ingredients"]
    except KeyError:
        redirect(url_for('add_recipe_info'))
    
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
        
        for counter, (k, v) in enumerate(session["added_recipe_ingredients"].items()):
        
        # Add check to see if ingredient, unit, amount has been added before, if so skip adding it and append from db
        
            ingreds = Ingredients(name=v["ingred"],
                              is_vegetarian = v["is_vegetarian"],
                              is_vegan=v["is_vegan"],
                              is_gluten_free=v["is_gluten_free"],
                              unit=v["unit"],
                              amount=v["amount"])
                              
            db.session.add(ingreds)
            temp_recipe.ingredients.append(ingreds)
        
        db.session.commit()
        
        
        session.pop("update_recipe")
        session.pop("update_recipe_ingredients")
        
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
            
    allergies = ['is_gluten_free','is_vegan','is_vegetarian']
    allergy_info = {}
    
    temp_allergy = {}
    for allergy in allergies:
        allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = 0))' % (recipe_result.id, allergy)).fetchall()
        allergy_info[allergy] = allergy_res[0][0]
    
    recipe_result_name_list = recipe_result.name.split(' ')

    related_recipe_result = []
    
    for word in recipe_result_name_list:
        temp_related = Recipe.query.filter(Recipe.name.like("%" + word + "%")).filter(Recipe.id != recipe_result.id)
        for temp_result in temp_related:
            if len(related_recipe_result) > 2:
                break
            if not temp_related in related_recipe_result:
                # Does this if work?
                related_recipe_result.append(temp_result)
        
    # related_recipes = []
    # while related_recipes > 3:
        
    
    return render_template('recipe.html', user=user, related_recipe_result=related_recipe_result, recipe_result=recipe_result, ingredients_result=ingredients_result, allergy_info=allergy_info)
    
@app.route('/account/my-recipes', methods=['POST', 'GET'])
def account_my_recipes():

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

    return redirect(url_for('index'))
    
@app.route('/mockdata')
def mockdata_create():
    
    user2 = User(first_name='Peta',last_name = 'Beckworth',username='pbeckworth1',password='5dDGrvV2Hf')
    user3 = User(first_name='Waiter',last_name = 'Bamsey',username='wbamsey2',password='Dn0RjPEw2Il')
    user4 = User(first_name='Tiffy',last_name = 'St. Pierre',username='tstpierre3',password='ZLiwuu')
    user5 = User(first_name='Wright',last_name = 'Hynes',username='whynes4',password='vjNLn6v9x')
    user6 = User(first_name='Giles',last_name = 'Muat',username='gmuat5',password='TH7Jnstr')
    user7 = User(first_name='Carena',last_name = 'Jaffa',username='cjaffa6',password='UhSkws')
    user8 = User(first_name='Shanan',last_name = 'Pankettman',username='spankettman7',password='IXAGUnKFm')
    user9 = User(first_name='Tom',last_name = 'Browse',username='tbrowse8',password='GKLlO76')
    user10 = User(first_name='Maximilianus',last_name = 'Dutton',username='mdutton9',password='dcguYxTbau')
    user11 = User(first_name='Freddie',last_name = 'Comiskey',username='fcomiskeya',password='bXthOP')
    user12 = User(first_name='Chryste',last_name = 'Mealand',username='cmealandb',password='NYzOHhKs5t')
    user13 = User(first_name='Carlotta',last_name = 'Ratke',username='cratkec',password='xWr8Fi')
    user14 = User(first_name='Cad',last_name = 'Esome',username='cesomed',password='L1flb5WX')
    user15 = User(first_name='Bunny',last_name = 'Mitchenson',username='bmitchensone',password='TAXQRKpb')
    user16 = User(first_name='Gertruda',last_name = 'Collyear',username='gcollyearf',password='UMKmvQl')
    user17 = User(first_name='Abe',last_name = 'Nurse',username='anurseg',password='aE2GcBHJwA')
    user18 = User(first_name='Rozina',last_name = 'Rippin',username='rrippinh',password='KcLPNkS')
    user19 = User(first_name='Mae',last_name = 'Stonier',username='mstonieri',password='aKEjJV5')
    user20 = User(first_name='Cesaro',last_name = 'Howard - Gater',username='chowardgaterj',password='nLvtBM8')
    user21 = User(first_name='Karisa',last_name = 'Kording',username='kkordingk',password='oIM5TidULK')
    user22 = User(first_name='Eartha',last_name = 'Roulston',username='eroulstonl',password='VlCYhJWGC')
    user23 = User(first_name='Pierson',last_name = 'Kimmons',username='pkimmonsm',password='AgGuzOYbH')
    user24 = User(first_name='Hirsch',last_name = 'Ripon',username='hriponn',password='tBq8AUK')
    user25 = User(first_name='Colet',last_name = 'Leggett',username='cleggetto',password='NH0Ygf')
    user26 = User(first_name='Brandyn',last_name = 'Selborne',username='bselbornep',password='tHKl2eD')
    user27 = User(first_name='Karlie',last_name = 'Cliffe',username='kcliffeq',password='omBgWggZ')
    user28 = User(first_name='Tye',last_name = 'Rollinshaw',username='trollinshawr',password='f9qDSGLsDy')
    user29 = User(first_name='Tiebold',last_name = 'Stuchberry',username='tstuchberrys',password='heo7wMH')
    user30 = User(first_name='Engracia',last_name = 'Linnell',username='elinnellt',password='l7W8jMpyUoq')
    user31 = User(first_name='Brinn',last_name = 'Espada',username='bespadau',password='2M0gGoi6th')
    user32 = User(first_name='Urbanus',last_name = 'Wiseman',username='uwisemanv',password='tSJR3At')
    user33 = User(first_name='Mufi',last_name = 'Dodamead',username='mdodameadw',password='M3PDCzRJ')
    user34 = User(first_name='Jean',last_name = 'Braysher',username='jbraysherx',password='9u6gzvS')
    user35 = User(first_name='Amargo',last_name = 'Anthona',username='aanthonay',password='IsDnJep')
    user36 = User(first_name='Lorianna',last_name = 'Wind',username='lwindz',password='iyf1BXH')
    user37 = User(first_name='Leif',last_name = 'Gradwell',username='lgradwell10',password='dG96frJdx')
    user38 = User(first_name='Jamie',last_name = 'Freake',username='jfreake11',password='RJvN1K0Vyn')
    user39 = User(first_name='Ermanno',last_name = 'Akaster',username='eakaster12',password='M8CMBB0')
    user40 = User(first_name='Gwyn',last_name = 'Kornalik',username='gkornalik13',password='Cg2gx1b')
    user41 = User(first_name='Meaghan',last_name = 'Scorton',username='mscorton14',password='53l7M9kj')
    user42 = User(first_name='Lion',last_name = 'Champion',username='lchampion15',password='DWq3f9ywZ7WR')
    user43 = User(first_name='Marcus',last_name = 'Bedfor',username='markymark',password='da3nKF34')
    user44 = User(first_name='Wake',last_name = 'Duffan',username='wduffan17',password='RUhUrnBg1Un2')
    user45 = User(first_name='Raynor',last_name = 'Grigori',username='rgrigori18',password='oTympA')
    user46 = User(first_name='Perry',last_name = 'Sullly',username='psullly19',password='WXq7IQLMEkw')
    user47 = User(first_name='Slade',last_name = 'Garz',username='sgarz1a',password='GtTqeg')
    user48 = User(first_name='Harry',last_name = 'Stevens',username='adljf3',password='Vz1h33r1')
    user49 = User(first_name='Cortney',last_name = 'Suermeiers',username='csuermeiers1c',password='ZcmAFHwS4Qx')
    user50 = User(first_name='Darryl',last_name = 'Loxley',username='dloxley1d',password='JIByGZ')
    
    db.session.add(user2)
    db.session.add(user3)
    db.session.add(user4)
    db.session.add(user5)
    db.session.add(user6)
    db.session.add(user7)
    db.session.add(user8)
    db.session.add(user9)
    db.session.add(user10)
    db.session.add(user11)
    db.session.add(user12)
    db.session.add(user13)
    db.session.add(user14)
    db.session.add(user15)
    db.session.add(user16)
    db.session.add(user17)
    db.session.add(user18)
    db.session.add(user19)
    db.session.add(user20)
    db.session.add(user21)
    db.session.add(user22)
    db.session.add(user23)
    db.session.add(user24)
    db.session.add(user25)
    db.session.add(user26)
    db.session.add(user27)
    db.session.add(user28)
    db.session.add(user29)
    db.session.add(user30)
    db.session.add(user31)
    db.session.add(user32)
    db.session.add(user33)
    db.session.add(user34)
    db.session.add(user35)
    db.session.add(user36)
    db.session.add(user37)
    db.session.add(user38)
    db.session.add(user39)
    db.session.add(user40)
    db.session.add(user41)
    db.session.add(user42)
    db.session.add(user43)
    db.session.add(user44)
    db.session.add(user45)
    db.session.add(user46)
    db.session.add(user47)
    db.session.add(user48)
    db.session.add(user49)
    db.session.add(user50)
    
    Recipe1= Recipe(name=u'pumpkin gnocchi',serves= 4,difficulty=u'easy',time=40,views=99,method=u"Steam the pumpkin in a colander set over a pan of simmering water or a steamer pan for 20 mins, or until very soft and tender.Using a potato masher, mash the steamed pumpkin to a smooth purée. Line a surface with kitchen paper and spread the pumpkin purée over before patting dry to ensure you remove as much moisture as possible.In a bowl or food processor, mix the pumpkin purée, ricotta, grated Parmesan, the egg, ¼ tsp salt and some black pepper. Stir well to combine, then add the flour and use a wooden spoon to mix to a soft dough, taking care not to ‘overmix’.Turn out the dough onto a floured surface and cut into 4. Roll each piece into a 1.5cm wide log. Cut the log into 2cm pieces using a floured knife. Gently mark each gnocchi with the back of a floured fork to achieve the traditional ridges.Bring a large pan of salted water to the boil. Tip in half the gnocchi and cook for 1-2 mins, until they rise to the surface. Remove with a slotted spoon and cook the remaining gnocchi.Heat 15g butter and the oil in a large frying pan. Add half the gnocchi and fry for 2 mins or until starting to brown. Add 15g more butter and, once melted, add the sage leaves. Fry for 1-2 mins, until the gnocchi are golden all over and the sage is crispy. Repeat with the remaining butter, gnocchi and sage leaves. Divide between serving plates. Season with a twist of black pepper and some shavings of Parmesan.",user_id=24,image_file=u'69432378.png')
    Ingredients1 = Ingredients(amount=u'400',name = u'pumpkin',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients1 = Ingredients(amount=u'120',name = u'ricotta',is_vegetarian=1,is_vegan=0,is_gluten_free=0,unit=u'g')
    Ingredients1 = Ingredients(amount=u'50',name = u'grated parmesan',is_vegetarian=1,is_vegan=0,is_gluten_free=0,unit=u'g')
    Ingredients1 = Ingredients(amount=u'1',name = u'egg',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients1 = Ingredients(amount=u'200',name = u'plain flour',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients1 = Ingredients(amount=u'60',name = u'salted butter',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients1 = Ingredients(amount=u'1',name = u'oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients1 = Ingredients(amount=u'20',name = u'sage leaves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe2= Recipe(name=u'crispy chicken with creamy mushrooms and braised leeks',serves= 1,difficulty=u'easy',time=10,views=62,method=u"Preheat the oven to gas 6, 200°C, fan 180°C. Heat 1 tbsp oil in a large frying pan over a medium heat and add the onions. Cook for 15-20 mins until softened and lightly golden. Transfer to a roasting tin and set aside.Add the mushrooms to the pan and turn the heat up to high. Cook for 8-10 mins until soft, then add to the roasting tin.Season the chicken thighs, add to the pan and reduce the heat to medium-high. Cook skin side down for 10 mins or until the skin is golden and crisp. Turn and cook for a further 5 mins. Transfer to the roasting tin and wipe the pan clean with kitchen paper.Pour the chicken stock into the roasting tin and roast for 25 mins or until the chicken is cooked through.Meanwhile, heat the remaining oil in the frying pan over a medium-high heat. Add the leeks, cut side down, and cook for 4 mins or until lightly golden. Using tongs, turn the leeks so the cut sides face up, then pour in 150ml hot water. Cover and simmer for 15-20 mins until tender.Transfer the chicken to a plate and cover with foil to keep warm. Put the mushrooms, onions and cooking juices in a saucepan, then stir in the crème fraîche, mustard and cornflour. Season to taste. Simmer for 2-3 mins until thickened.Divide the chicken and sauce between plates and serve the leeks alongside. Garnish with the parsley and a twist of black pepper.",user_id=6,image_file=u'69432378.png')
    Ingredients3 = Ingredients(amount=u'2',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients4 = Ingredients(amount=u'2',name = u'onions',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients5 = Ingredients(amount=u'250',name = u'closed cup mushrooms',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients6 = Ingredients(amount=u'8',name = u'chicken thighs',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients7 = Ingredients(amount=u'400',name = u'chicken stock',is_vegetarian=0,is_vegan=0,is_gluten_free=0,unit=u'ml')
    Ingredients8 = Ingredients(amount=u'100',name = u'half-fat crème fraîche',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'ml')
    Ingredients9 = Ingredients(amount=u'2',name = u'Dijon mustard',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'heaped tsp')
    Ingredients10 = Ingredients(amount=u'1 1/2',name = u'cornflour',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'tsp')
    Ingredients11 = Ingredients(amount=u'1',name = u'chopped parsley',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients12 = Ingredients(amount=u'2',name = u'leeks',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe3= Recipe(name=u'one-pot linguine with olives, capers and sundried tomatoes recipe',serves= 4,difficulty=u'medium',time=20,views=15,method=u"Pour the passata into a large saucepan and stir in the olives, capers, sundried tomatoes, 1 tsp salt and 500ml water. Bring to a simmer.Add the pasta, and use tongs to stir the pasta into the sauce as it softens. Continue to cook, uncovered, for 11-12 mins, until the pasta is cooked but still al dente and the sauce is reduced and coats the pasta.",user_id=8,image_file=u'69432378.png')
    Ingredients13 = Ingredients(amount=u'500',name = u'carton passata with basil',is_vegetarian=1,is_vegan=0,is_gluten_free=0,unit=u'g')
    Ingredients14 = Ingredients(amount=u'75',name = u'pitted black olives',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients15 = Ingredients(amount=u'30',name = u'capucine capers',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients16 = Ingredients(amount=u'75',name = u'sundried tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients17 = Ingredients(amount=u'350',name = u'linguine',is_vegetarian=1,is_vegan=0,is_gluten_free=0,unit=u'g')
    Recipe4= Recipe(name=u'barbecue sausage and mixed bean bake recipe',serves= 2,difficulty=u'hard',time=100,views=65,method=u"Preheat the oven to gas 6, 200°C, fan 180°C. Put the oil in a roasting tin and heat in the oven for 10 mins. Add the sausages and sliced onion, toss to coat in the hot oil and roast for 10 mins.Meanwhile, preheat a griddle pan or heavy frying pan. Griddle the corn for 15 mins, turning occasionally, until charred and tender. Remove the kernels carefully by standing the cob firmly on a chopping board and slicing with a sharp knife.Remove the sausages from the oven and stir in the beans, tomatoes and barbecue sauce; season. Bake for 15 mins until the sauce is bubbling and the sausages are cooked through.Meanwhile, make the salsa. In a small bowl, mix the corn, diced red onion and parsley. Serve scattered over the sausages and beans.",user_id=29,image_file=u'69432378.png')
    Ingredients18 = Ingredients(amount=u'2',name = u'vegetable oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients19 = Ingredients(amount=u'8',name = u'pork sausages',is_vegetarian=0,is_vegan=0,is_gluten_free=0,unit=u'')
    Ingredients20 = Ingredients(amount=u'1',name = u'red onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients21 = Ingredients(amount=u'2',name = u'corn on the cob',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients22 = Ingredients(amount=u'800',name = u'mixed bean salad',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients23 = Ingredients(amount=u'400',name = u'tin Italian chopped tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients24 = Ingredients(amount=u'3',name = u'barbecue sauce',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients25 = Ingredients(amount=u'10',name = u'fresh flat-leaf parsley',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Recipe5= Recipe(name=u'banana and blackberry smoothie bowls with figs recipe',serves= 2,difficulty=u'hard',time=10,views=36,method=u"Toast the seeds in a small frying pan over a medium heat for 1-2 mins until just golden. Set aside.Put the bananas, 125g blackberries and 60g yogurt in a blender with the apple juice and oats; blitz to a thick smoothie-like consistency, scraping down the sides with a spatula if necessary. Add lemon juice to taste, if you like. Divide between 2 bowls and spoon through the remaining yogurt to create a swirl effect.Arrange the sliced figs and the remaining blackberries on top, then scatter over the toasted seeds to serve",user_id=3,image_file=u'69432378.png')
    Ingredients26 = Ingredients(amount=u'2',name = u'pumpkin seeds',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients27 = Ingredients(amount=u'2',name = u'sunflower seeds',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients28 = Ingredients(amount=u'',name = u'small bananas',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients29 = Ingredients(amount=u'150',name = u'blackberries',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients30 = Ingredients(amount=u'75',name = u'greek-style yogurt',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients31 = Ingredients(amount=u'50',name = u'apple juice',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients32 = Ingredients(amount=u'1',name = u'porridge oats',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'tsp')
    Ingredients33 = Ingredients(amount=u'20',name = u'lemon juice',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients34 = Ingredients(amount=u'2',name = u'small ripe figs',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe6= Recipe(name=u'kale, poached egg and smoked salmon toast topper recipe',serves= 1,difficulty=u'hard',time=10,views=147,method=u"Poach the egg for 3 mins for a runny yolk or 4 mins for a set yolk. Remove and drain on kitchen paper.Meanwhile, toast the bread. Put the kale in a colander and pour over boiling water to wilt.Drizzle the toast with oil, then top with the kale, smoked salmon, the egg and chilli.",user_id=43,image_file=u'69432378.png')
    Ingredients35 = Ingredients(amount=u'1',name = u'egg',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients36 = Ingredients(amount=u'1',name = u'rye and sunflower bread',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'slice')
    Ingredients37 = Ingredients(amount=u'25',name = u'curly kale',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients38 = Ingredients(amount=u'1',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients39 = Ingredients(amount=u'30',name = u'smoked salmon',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients40 = Ingredients(amount=u'43469',name = u'red chilli',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe7= Recipe(name=u'kale and cauliflower cheese recipe',serves= 1,difficulty=u'medium',time=50,views=55,method=u"Bring a pan of lightly salted water to the boil and cook the cauliflower for 10 minutes. Add the kale to the top of the pan and cook for a further 2 minutes, then drain well and set aside.Preheat the oven to gas 7, 220ºC, fan 200ºC. Meanwhile, melt the butter in a pan, then add the flour and cook over a low heat for 1 minute, stirring continually. Add the mustard powder, stir and remove from the heat. Gradually add the milk a little at a time, stirring well to beat out any lumps.Return to the heat and bring to a simmer, stirring all the time. Once bubbling, cook for 2-3 minutes until thickened.Stir in ⅔ of the Cheddar, half of the Manchego and half of the vegetarian hard cheese and beat well. Add the mustard and pepper and beat again. Add the drained cauliflower and kale to the sauce and toss well to coat. Transfer to a 2 pint gratin dish.Mix the remaining cheeses together and scatter over the top. Bake for 20 minutes until golden and cooked through. Serve with roast chicken or gammon as a delicious side dish.",user_id=50,image_file=u'69432378.png')
    Ingredients41 = Ingredients(amount=u'1',name = u'cauliflower',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients42 = Ingredients(amount=u'150',name = u'kale',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients43 = Ingredients(amount=u'50',name = u'butter',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients44 = Ingredients(amount=u'50',name = u'plain flour',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients45 = Ingredients(amount=u'2',name = u'mustard powder',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'tsp')
    Ingredients46 = Ingredients(amount=u'500',name = u'milk',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'ml')
    Ingredients47 = Ingredients(amount=u'100',name = u'mature cheddar cheese',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients48 = Ingredients(amount=u'75',name = u'manchego cheese',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients49 = Ingredients(amount=u'50',name = u'italian-style hard cheese',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients50 = Ingredients(amount=u'1',name = u'wholegrain mustard',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients51 = Ingredients(amount=u'43467',name = u'ground black pepper',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Recipe8= Recipe(name=u'celeriac, kale and potato gratin recipe',serves= 2,difficulty=u'medium',time=180,views=45,method=u"Preheat the oven to gas 2, 150°C, fan 130°C. Combine the cream, milk, garlic, sage and mustard in a pan. Heat until just coming to the boil, then remove and season with a little freshly grated nutmeg. Discard the sage.Meanwhile, blanch the kale for 1 minute in a pan of gently simmering water, then drain and refresh in cold water. Drain again, then dry with kitchen paper.Grease a baking dish with butter. Pour in a little of the cream mixture. Top with a layer of celeriac and potato, season, then top with a little kale. Repeat until all the ingredients are used up, finishing with a layer of the cream mixture. Cover with foil and bake for 1 hour 40 minutes.Heat the grill to medium. Remove the foil and finish off under the grill, until golden.",user_id=46,image_file=u'69432378.png')
    Ingredients52 = Ingredients(amount=u'100',name = u'double cream',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'ml')
    Ingredients53 = Ingredients(amount=u'75',name = u'semi-skimmed milk',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'ml')
    Ingredients54 = Ingredients(amount=u'1',name = u'garlic clove',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients55 = Ingredients(amount=u'3',name = u'sage leaves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients56 = Ingredients(amount=u'1',name = u'dijon mustard',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients57 = Ingredients(amount=u'',name = u'nutmeg',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients58 = Ingredients(amount=u'25',name = u'kale',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients59 = Ingredients(amount=u'',name = u'butter',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients60 = Ingredients(amount=u'100',name = u'celeriac',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients61 = Ingredients(amount=u'150',name = u'potatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Recipe9= Recipe(name=u'pear and broccoli soup recipe',serves= 4,difficulty=u'easy',time=30,views=64,method=u"Heat the oil in a large saucepan over a medium heat. Add the onion and cook, stirring occasionally, for 6-8 mins until soft. Add the broccoli, pears and vegetable stock. Season, then bring to the boil. Cover, reduce the heat to low and cook for 10-12 mins or until the broccoli is soft.Using a hand blender, blitz the soup until smooth. Divide between 4 bowls and top each with the blue cheese, cranberries, walnuts and a drizzle of oil to serve.",user_id=49,image_file=u'69432378.png')
    Ingredients62 = Ingredients(amount=u'2',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients63 = Ingredients(amount=u'1',name = u'onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients64 = Ingredients(amount=u'2',name = u'broccoli',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients65 = Ingredients(amount=u'2',name = u'conference pears',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients66 = Ingredients(amount=u'850',name = u'hot vegetable stock',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients67 = Ingredients(amount=u'60',name = u'vegetarian blue cheese',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients68 = Ingredients(amount=u'20',name = u'dried cranberries',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients69 = Ingredients(amount=u'20',name = u'walnuts',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Recipe10= Recipe(name=u'frittata wraps',serves= 2,difficulty=u'easy',time=30,views=113,method=u"Heat the oil in a 25cm nonstick frying pan over a medium heat. Add the onion and garlic. Cook, stirring occasionally, for 5-6 mins until softened. Meanwhile, beat the eggs in a large bowl, then add the peas and tomatoes; season.Add the mixture to the frying pan and cook over a medium heat for 15 mins, then grill for 5 mins until set. Leave to cool, then loosen around the edges with a spatula and slide onto a board. Cut in half.Divide a frittata half into 4. Lay the wraps on a board and spread each with the soured cream. Divide the chilli between them and add the salad leaves. Top with the frittata pieces; roll up, cut in half and store in a sealed lunchbox in the fridge until ready to eat.",user_id=32,image_file=u'69432378.png')
    Ingredients70 = Ingredients(amount=u'1',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients71 = Ingredients(amount=u'43467',name = u'onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients72 = Ingredients(amount=u'1',name = u'garlic clove',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients73 = Ingredients(amount=u'6',name = u'eggs',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients74 = Ingredients(amount=u'150',name = u'peas',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients75 = Ingredients(amount=u'125',name = u'cherry tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients76 = Ingredients(amount=u'2',name = u'tortilla wraps',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'')
    Ingredients77 = Ingredients(amount=u'2',name = u'cream',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'tbsp')
    Ingredients78 = Ingredients(amount=u'1',name = u'red chilli',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients79 = Ingredients(amount=u'2',name = u'salad leaves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'handfuls')
    Recipe11= Recipe(name=u'teriyaki chicken noodles',serves= 4,difficulty=u'medium',time=30,views=90,method=u"In a bowl, mix the chicken with the teriyaki sauce. Set aside in the fridge to marinate for 15 mins.Meanwhile, cook the noodles to pack instructions. Drain well, then toss with the sesame oil and soy sauce.Bring a large pan of water to the boil and add the broccoli. Cook for 5 mins, adding the mangetout for the final 3 mins. Drain and set aside.Heat a large griddle pan over a high heat until hot and almost smoking. Working in batches, griddle the chicken, pouring over any marinade left in the bowl, for 1-2 mins each side until fully cooked through.To serve, divide the noodles between plates and top with the veg and griddled chicken. Garnish with the chilli, spring onions and sesame seeds, and drizzle with a little extra sesame oil, if you like.",user_id=32,image_file=u'69432378.png')
    Ingredients80 = Ingredients(amount=u'650',name = u'chicken breast',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients81 = Ingredients(amount=u'3 1/2',name = u'teriyaki sauce',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients82 = Ingredients(amount=u'250',name = u'dreid medium egg noodles',is_vegetarian=0,is_vegan=0,is_gluten_free=0,unit=u'g')
    Ingredients83 = Ingredients(amount=u'1',name = u'sesame oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients84 = Ingredients(amount=u'1',name = u'soy sauce',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients85 = Ingredients(amount=u'1',name = u'broccoli',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients86 = Ingredients(amount=u'85',name = u'mangetout',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients87 = Ingredients(amount=u'1',name = u'red chilli',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients88 = Ingredients(amount=u'3',name = u'spring onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients89 = Ingredients(amount=u'1',name = u'sesame seeds',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Recipe12= Recipe(name=u'chicken and tomato spiced curry recipe',serves= 4,difficulty=u'hard',time=30,views=164,method=u"Heat 1 tbsp of the oil in a large flameproof casserole dish set over a high heat. Working in batches if necessary, cook the chicken for 5-7 mins until golden and just cooked through, then remove and set aside.Put the remaining oil in the dish. Add the onion, cook for 3 mins until soft, then add the red pepper and cook for 2 mins. Stir in the garlic and ginger and cook for 30 secs. Stir in the curry paste until everything is well coated.Pour in the tomatoes along with 200ml water. Bring to the boil, then reduce the heat, cover the dish and leave to simmer for 10 mins until the sauce has thickened a little. Return the chicken to the dish and cook for 5 mins, uncovered, until piping hot and cooked through.Meanwhile, cook the basmati rice following pack instructions. Serve with the curry and sprinkle over the coriander to finish.",user_id=5,image_file=u'69432378.png')
    Ingredients90 = Ingredients(amount=u'2',name = u'vegetable oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients91 = Ingredients(amount=u'450',name = u'chicken breast',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients92 = Ingredients(amount=u'1',name = u'onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients93 = Ingredients(amount=u'1',name = u'red pepper',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients94 = Ingredients(amount=u'2',name = u'garlic cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients95 = Ingredients(amount=u'1',name = u'piece ginger',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'cm')
    Ingredients96 = Ingredients(amount=u'2',name = u'madras curry paste',is_vegetarian=1,is_vegan=0,is_gluten_free=0,unit=u'tbsp')
    Ingredients97 = Ingredients(amount=u'400',name = u'chopped tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients98 = Ingredients(amount=u'300',name = u'basmati rice',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients99 = Ingredients(amount=u'1',name = u'coriander',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'handful')
    Recipe13= Recipe(name=u'gluten-free spaghetti bolognese recipe',serves= 4,difficulty=u'medium',time=180,views=13,method=u"Heat the oil in a large and sauté the onions and garlic, frying until softened. Increase the heat and add the minced beef.Fry it until it has browned, breaking down any chunks of meat with a wooden spoon. Pour in the wine and boil until it has reduced a little. Reduce the temperature and stir in the mushrooms, tomatoes and sundried tomatoes. Bring to the boil, cover and simmer for 1 hour stirring from time to time.At the end of cooking add the basil and parsley. Cook the gluten free pasta according to the packet instructions. Drain and divide between 4 warmed bowls. Ladle over the cooked bolognese sauce and finish with a sprinkling of Parmesan cheese.",user_id=1,image_file=u'69432378.png')
    Ingredients100 = Ingredients(amount=u'2',name = u'rapeseed oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients101 = Ingredients(amount=u'2',name = u'onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients102 = Ingredients(amount=u'4',name = u'garlic cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients103 = Ingredients(amount=u'500',name = u'lean beef mince',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients104 = Ingredients(amount=u'100',name = u'red wine',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients105 = Ingredients(amount=u'150',name = u'button mushrooms',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients106 = Ingredients(amount=u'780',name = u'chopped tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients107 = Ingredients(amount=u'6',name = u'sun dried tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients108 = Ingredients(amount=u'2',name = u'fresh basil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients109 = Ingredients(amount=u'2',name = u'fresh parsley',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients110 = Ingredients(amount=u'',name = u'salt',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients111 = Ingredients(amount=u'',name = u'ground black pepper',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients112 = Ingredients(amount=u'400',name = u'gluten-free spaghetti',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients113 = Ingredients(amount=u'',name = u'parmesan cheese',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'')
    Recipe14= Recipe(name=u'earl grey ham recipe',serves= 1,difficulty=u'easy',time=130,views=112,method=u"Preheat the oven to gas 5, 190°C, fan 170°C. Put the tea bags in a large measuring jug and cover with 350ml (12fl oz) boiled water. Set aside to brew. In a bowl, combine the sugar and mustard to make a thick paste.Using a sharp knife, pare the skin from the gammon joint, leaving a good layer of fat still attached to the meat. Score the fat in a criss-cross pattern and push cloves into the points where the scored lines cross. transfer to a small roasting tin, fat side up, and spoon over the mustard mixture in a thick, even layer.Squeeze the liquid out of the tea bags and discard. Pour the tea around the joint, then cover loosely with foil and cook for 2 hrs (or for 30 mins, plus 30 mins per 500g (1lb)), until cooked through. Remove the foil for the last 20 mins of cooking. Rest the ham for 10 mins, before carving.",user_id=3,image_file=u'69432378.png')
    Ingredients114 = Ingredients(amount=u'4',name = u'Earl Grey tea bags',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients115 = Ingredients(amount=u'50',name = u'light brown soft sugar',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients116 = Ingredients(amount=u'50',name = u'dijon mustard',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients117 = Ingredients(amount=u'1-1.5',name = u'unsmoked gammon joint',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'kg')
    Ingredients118 = Ingredients(amount=u'30',name = u'whole cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe15= Recipe(name=u'mushroom and feta risotto',serves= 2,difficulty=u'easy',time=50,views=178,method=u"Put the dried mushrooms in a heatproof jug, cover with 500ml boiling water and set aside. Meanwhile, heat 1 tbsp oil in a deep, wide frying pan and fry the chestnut mushrooms over a high heat for 4-5 mins until deep brown. Remove and set aside.Add the remaining ½ tbsp oil to the pan and fry the onions and garlic over a medium heat for 6-8 mins until soft and beginning to caramelise.Strain the dried mushrooms, reserving the liquid, then roughly chop and add to the pan. Add the rice and stir well. Stir in the wine and cook until the rice has absorbed it. Return the chestnut mushrooms to the pan then add the reserved mushroom liquid, a ladle at a time, stirring constantly. Wait until the rice has absorbed most of the liquid before adding more. Repeat until you've used all the liquid – this should take 20-25 mins.Once the rice is tender but with a little bite, season to taste. Stir through the spinach leaves until wilted. Divide between 2 plates and top with the feta.",user_id=29,image_file=u'69432378.png')
    Ingredients119 = Ingredients(amount=u'15',name = u'dried porcini mushrooms',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients120 = Ingredients(amount=u'1 1/2',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients121 = Ingredients(amount=u'150',name = u'chestnut mushrooms',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients122 = Ingredients(amount=u'1',name = u'small onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients123 = Ingredients(amount=u'1',name = u'garlic clove',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients124 = Ingredients(amount=u'140',name = u'arborio rice',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients125 = Ingredients(amount=u'75',name = u'white wine',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients126 = Ingredients(amount=u'100',name = u'baby spinach',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients127 = Ingredients(amount=u'50',name = u'feta',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Recipe16= Recipe(name=u'parsnip and ginger soup with spiced roast chickpeas recipe',serves= 4,difficulty=u'easy',time=40,views=24,method=u"Preheat the oven to gas 7, 220°C, fan 200°C, and line a baking tray with nonstick baking paper. Heat 1 tbsp oil in a large saucepan over a medium heat and fry the onion for 5 mins to soften. Stir through the garlic, ginger and 1 tsp cumin and cook for 1 min.Add the parsnips, season and pour in the stock. Bring to the boil, then reduce the heat to medium-low and simmer for 25 mins until the parsnips are very tender.Meanwhile, toss the chickpeas with 1 tbsp oil, the ground coriander and remaining cumin. Arrange in a single layer on the lined tray and roast for 20-25 mins until golden and crisp.Use a food processor or hand blender to blend the soup until smooth. Reheat if necessary, then season to taste with black pepper and lemon juice and divide between 4 bowls. Toss the roasted chickpeas with the fresh coriander and scatter over the soup to serve.",user_id=2,image_file=u'69432378.png')
    Ingredients128 = Ingredients(amount=u'2',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients129 = Ingredients(amount=u'1',name = u'large onion',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients130 = Ingredients(amount=u'2',name = u'garlic cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients131 = Ingredients(amount=u'5',name = u'ginger',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'cm piece')
    Ingredients132 = Ingredients(amount=u'1 1/4',name = u'ground cumin',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'tsp')
    Ingredients133 = Ingredients(amount=u'500',name = u'parsnips',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients134 = Ingredients(amount=u'1',name = u'vegetable stock cube',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients135 = Ingredients(amount=u'400',name = u'chickpeas',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients136 = Ingredients(amount=u'43467',name = u'ground coriander',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients137 = Ingredients(amount=u'',name = u'lemon juice',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients138 = Ingredients(amount=u'10',name = u'fresh coriander',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Recipe17= Recipe(name=u'channa dhal recipe',serves= 4,difficulty=u'medium',time=40,views=137,method=u"Drain the lentils and put in a pan with 800ml fresh water. Bring to the boil and cook on a moderate heat for approximately 35 minutes or until they are well cooked and have gone mushy.In a separate pan heat the oil, add the cumin seeds, mustard seeds, curry leaves and asafoetida (if using) and cook for approximately 1 minute taking care not to burn the mixture.Add the Patak's Madras Paste and cook for a further 1 minute. Add the tomatoes and allow to cook for 2 minutes.Remove the pan from the heat and add all the mixture to the cooked lentils. Check the seasoning, and adjust the salt and add the sugar. Squeeze in the lemon juice and stir through the chopped fresh coriander. Serve with chapattis and rice.",user_id=38,image_file=u'69432378.png')
    Ingredients139 = Ingredients(amount=u'250',name = u'dried yellow split peas / lentils',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients140 = Ingredients(amount=u'2',name = u'vegetable oil or ghee',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients141 = Ingredients(amount=u'1',name = u'cumin seeds',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients142 = Ingredients(amount=u'1',name = u'curry leaves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'handful')
    Ingredients143 = Ingredients(amount=u'1',name = u'mustard seeds',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients144 = Ingredients(amount=u'',name = u'pinch asafoetida',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients145 = Ingredients(amount=u'',name = u'salt',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients146 = Ingredients(amount=u'1',name = u'sugar',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients147 = Ingredients(amount=u'2',name = u'fresh coriander',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients148 = Ingredients(amount=u'43467',name = u'lemon',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients149 = Ingredients(amount=u'1',name = u'madras paste',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients150 = Ingredients(amount=u'2',name = u'medium tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe18= Recipe(name=u'vegan butternut squash spaghetti with rocket and hazelnut pesto recipe',serves= 4,difficulty=u'medium',time=20,views=168,method=u"Put 25g hazelnuts, half the garlic and 50g rocket in a food processor and pulse a few times until roughly chopped. Add 125ml oil and the lemon juice then blend again until combined but not completely smooth – you want a pesto with a little bit of texture. Season to taste and set aside.Use a spiralizer to cut the squash quarters into thin ribbons (depending on the size of your spiralizer you may need to cut the squash into thinner wedges). If you don’t have a spiralizer, you can cut the squash into thin wedges then use a vegetable peeler to peel off ribbons.Heat the remaining oil in a large, wide pan, then add the squash ribbons and sauté for 2-3 mins – you may need to do this in batches. Add the remaining garlic and a splash of water to help the squash steam gently. Cook for 2 mins, trying not to stir too much as the squash may break up.Stir most of the rocket pesto into the pan (reserving some to serve) so that it just coats the squash and heats through.Divide the squash spaghetti between plates and top with the remaining rocket leaves, chopped hazelnuts and grated lemon zest. Drizzle over the remaining pesto and serve with a lemon wedge on the side to squeeze over.",user_id=35,image_file=u'69432378.png')
    Ingredients151 = Ingredients(amount=u'40',name = u'toasted hazelnuts',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients152 = Ingredients(amount=u'2',name = u'garlic cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients153 = Ingredients(amount=u'70',name = u'wild rocket',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients154 = Ingredients(amount=u'155',name = u'extra-virgin olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients155 = Ingredients(amount=u'43467',name = u'lemon',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients156 = Ingredients(amount=u'1',name = u'butternut squash',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe19= Recipe(name=u'vegan roasted carrot risotto recipe',serves= 4,difficulty=u'medium',time=50,views=124,method=u"Preheat the oven to gas 7, 220°C, fan 200°C. Heat 3 tbsp of the oil in a wide saucepan or deep frying pan over a low heat. Add the onion, celery and the crushed garlic cloves. Pick the leaves from half the thyme sprigs and add to the pan along with a pinch of salt. Cover and cook gently for 10 mins or until softened, stirring occasionally.Meanwhile, place the carrots in a roasting tray with the whole garlic cloves and remaining thyme sprigs. Drizzle with the remaining 1 tbsp oil and season. Roast for 20-25 mins until just tender and slightly charred.Add the risotto rice to the onion mix and stir for 2 mins to toast the rice, then increase the heat to medium. Add the sherry (or wine) and simmer until the liquid has been absorbed. Add the hot stock one ladle at a time, stirring constantly and allowing the liquid to absorb each time before adding the next ladleful. Stop when you have about 2 ladles remaining.Remove the roasted carrots from the oven and discard the thyme sprigs. Set aside 12 of the carrots to serve, keeping warm. Add the rest of the carrots and garlic cloves (squeezed from their skins) to a food processor or blender with the remaining stock and blitz to a rough purée. Stir through the rice until fully combined, cooking for a final few minutes until the rice is tender.Add the seeds to a dry frying pan with a pinch of salt and toast for 2 mins over a medium heat, shaking the pan regularly to stop them burning. Serve the risotto garnished with the reserved carrots and toasted seeds sprinkled over.",user_id=46,image_file=u'69432378.png')
    Ingredients157 = Ingredients(amount=u'4',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients158 = Ingredients(amount=u'4',name = u'onions',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients159 = Ingredients(amount=u'2',name = u'celery sticks',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients160 = Ingredients(amount=u'4',name = u'garlic cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients161 = Ingredients(amount=u'7.5',name = u'thyme',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients162 = Ingredients(amount=u'1',name = u'bunched carrots',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'pack')
    Ingredients163 = Ingredients(amount=u'300',name = u'risotto rice',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients164 = Ingredients(amount=u'100',name = u'vegan dry sherry',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ml')
    Ingredients165 = Ingredients(amount=u'1.25',name = u'vegan vegetable stock',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'ltr')
    Ingredients166 = Ingredients(amount=u'3',name = u'4 seed mix',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'tbsp')
    Recipe20= Recipe(name=u'baked herby carrots',serves= 4,difficulty=u'medium',time=50,views=89,method=u"Preheat the oven to gas 6, 200°C, fan 180°C and cut a 50cm length of nonstick baking paper. Fold it in half lengthways, then open up and put it on a baking sheet.Toss the carrots in a bowl with the bay leaf, garlic and seasoning. Lay the carrots along the crease of the paper and dot over the butter. Make a parcel by bringing the paper up over the carrots, folding the top to seal, then fold up the short ends. Bake for 40 minutes. Serve opened and sprinkled with herbs.",user_id=43,image_file=u'69432378.png')
    Ingredients167 = Ingredients(amount=u'450',name = u'tendersweet carrots',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients168 = Ingredients(amount=u'1',name = u'dried bay leaf',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients169 = Ingredients(amount=u'5',name = u'garlic cloves',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients170 = Ingredients(amount=u'2',name = u'butter',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients171 = Ingredients(amount=u'',name = u'fresh herbs',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe21= Recipe(name=u'roasted maple and cumin roots',serves= 3,difficulty=u'hard',time=60,views=84,method=u"Preheat the oven to gas 6, 200°C, fan 180°C. Slice the carrots and parsnips lengthways in half (or quarter, if large). Chop the beetroot and celeriac into evenly sized chunks or wedges. Arrange in a roasting tin.Drizzle the veg with the oil and scatter over the cumin and thyme. Season well and toss to coat. Nestle the garlic halves in the tin, cut-sides up. Roast for 35 minutes, turning occasionally, until the veg is softened.Meanwhile, in a jug, mix the maple syrup with the mustard. Remove the roots from the oven and drizzle over the maple mixture. Toss to coat, then return to the oven for 10-15 minutes more, until golden.",user_id=39,image_file=u'69432378.png')
    Ingredients172 = Ingredients(amount=u'300',name = u'carrots',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients173 = Ingredients(amount=u'300',name = u'parsnips',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients174 = Ingredients(amount=u'300',name = u'beetroot',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients175 = Ingredients(amount=u'300',name = u'celeriac',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients176 = Ingredients(amount=u'2',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients177 = Ingredients(amount=u'1 1/2',name = u'cumin seeds',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients178 = Ingredients(amount=u'1',name = u'thyme prigs',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'handful')
    Ingredients179 = Ingredients(amount=u'1',name = u'garlic bulb',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients180 = Ingredients(amount=u'3',name = u'maple syrup',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients181 = Ingredients(amount=u'1',name = u'dijon mustard',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Recipe22= Recipe(name=u'florentine pizza',serves= 4,difficulty=u'hard',time=30,views=103,method=u"To make the pizza dough, mix the flour, sugar, 2 tsp salt, and yeast in a bowl. Stir in the oil and add about 300ml lukewarm water to make a soft, but not sticky dough.Tip onto a floured work surface and knead for 10 mins. Transfer to a clean bowl, cover with oiled clingfilm and set aside to prove in a warm place for 1 hr, or until doubled in size.Meanwhile, cook the tomatoes in a pan until thickened and reduced; season well. Preheat the oven to its highest setting. Divide the dough into 4 and shape each into a ball. Roll out thinly and put on 4 baking sheets lined with nonstick baking paper.Spread each base with tomato sauce, then scatter over the spinach, mozzarella and ham. Bake, in batches if needed, for 8 mins.Crack an egg in the centre of each pizza. Continue baking for 2-3 mins more, until the egg is just set and the crust is crisp.",user_id=47,image_file=u'69432378.png')
    Ingredients182 = Ingredients(amount=u'400',name = u'chopped tomatoes',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients183 = Ingredients(amount=u'240',name = u'baby spinach',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients184 = Ingredients(amount=u'125',name = u'mozzarella ball',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients185 = Ingredients(amount=u'250',name = u'grated mozzarella',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients186 = Ingredients(amount=u'88',name = u'parma ham',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients187 = Ingredients(amount=u'4',name = u'eggs',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients188 = Ingredients(amount=u'500',name = u'strong bread flour',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients189 = Ingredients(amount=u'1',name = u'caster sugar',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients190 = Ingredients(amount=u'14',name = u'dreid yeast',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients191 = Ingredients(amount=u'2',name = u'extra-virgin olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Recipe23= Recipe(name=u'star pizzas',serves= 4,difficulty=u'medium',time=30,views=181,method=u"Preheat the grill to medium high. Flatten the bread slightly by rolling with a rolling pin, then cut out different shapes (stars, hearts or whatever you have to hand) using biscuit cutters. Place on a baking sheet, brush with the oil and grill for 3-4 minutes or until just turning golden.Turn the bread shapes over and spread with the basil and tomato sauce. Add the ham or pepperoni and top with the mozzarella pearls. Grill for a further 5-6 minutes or until the cheese has melted and is turning golden.",user_id=19,image_file=u'69432378.png')
    Ingredients192 = Ingredients(amount=u'4',name = u'white medium bread',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'slices')
    Ingredients193 = Ingredients(amount=u'2',name = u'olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients194 = Ingredients(amount=u'50',name = u'fresh basil and tomato sauce',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients195 = Ingredients(amount=u'2',name = u'parma ham',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'slices')
    Ingredients196 = Ingredients(amount=u'100',name = u'mozzarella pearls',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Recipe24= Recipe(name=u'free-from apple crumble',serves= 2,difficulty=u'hard',time=60,views=110,method=u"Preheat the oven to gas 5, 190°C, fan 170°C. Put the apples in a 25 x 16cm ovenproof dish at least 5cm deep.Pour over the lemon juice and toss to coat. Scatter over the sultanas and cinnamon, then drizzle with 60g maple syrup. Mix well, then put the dish on a baking tray and bake for 10 mins.Meanwhile, mix the flour and oats in a large bowl. Rub in the spread with your fingertips, then stir in the nuts, cranberries and 100g maple syrup until just combined. Don't overmix as it can become sticky.Scatter the topping over the baked apple mixture but don’t pack it down. Bake for a further 35 mins or until lightly golden-brown on top and bubbling at the edges. Leave to cool slightly, then serve with dairy-free cream or ice cream, if you like.",user_id=16,image_file=u'69432378.png')
    Ingredients197 = Ingredients(amount=u'3',name = u'Bramley apples',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients198 = Ingredients(amount=u'43467',name = u'lemon',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients199 = Ingredients(amount=u'60',name = u'sultanas',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients200 = Ingredients(amount=u'2',name = u'ground cinnamon',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients201 = Ingredients(amount=u'60',name = u'maple syrup',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients202 = Ingredients(amount=u'175',name = u'gluten-free plain flour',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients203 = Ingredients(amount=u'90',name = u'gluten-free plain oats',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients204 = Ingredients(amount=u'90',name = u'coconut oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients205 = Ingredients(amount=u'50',name = u'pecans',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients206 = Ingredients(amount=u'50',name = u'hazelnuts',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients207 = Ingredients(amount=u'50',name = u'dried cranberries',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients208 = Ingredients(amount=u'100',name = u'maple syrup',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients209 = Ingredients(amount=u'',name = u'dairy free ice cream',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Recipe25= Recipe(name=u'ricotta, pea and mint ravioli',serves= 4,difficulty=u'hard',time=70,views=123,method=u"Briefly blitz the flour and salt in a food processor. Add the eggs and blitz for 1 min or until it resembles breadcrumbs. Tip out onto a lightly floured surface. Knead for 5-10 mins until you have a smooth, soft dough. Shape into a ball, wrap in clingfilm and chill in the fridge for at least 30 mins.Meanwhile, boil half the peas for 3 mins. Drain, run under cold water to cool, then drain well. Put in a bowl with 1 tbsp oil and crush with a fork. Stir in the ricotta, chives and chopped mint; season. Cover with clingfilm and chill.Divide the pasta dough into 4 pieces, wrap 3 in clingfilm and return them to the fridge. On a lightly floured surface, roll out the other piece to 15 x 50cm.Place 5 heaped teaspoons of filling along a long side of the pasta, with a 2cm border along the edge and about 4cm between each scoop. Fold the pasta in half lengthways over the filling and press down around it. Cut into 5 ravioli and use a fork to seal the edges. Dust with flour and set aside. Repeat with the remaining pasta and filling.Bring a very large pan of salted water to the boil. Add the ravioli one by one, then the remaining peas. Cook for 4 mins until al dente. Gently drain and return to the pan. Add the remaining oil and the zest; gently toss to coat. Season with black pepper, scatter over the reserved mint leaves and serve with the lemon slices and grated cheese.",user_id=29,image_file=u'69432378.png')
    Ingredients210 = Ingredients(amount=u'300',name = u'plain flour',is_vegetarian=1,is_vegan=1,is_gluten_free=0,unit=u'g')
    Ingredients211 = Ingredients(amount=u'43467',name = u'salt',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tsp')
    Ingredients212 = Ingredients(amount=u'3',name = u'eggs',is_vegetarian=0,is_vegan=0,is_gluten_free=1,unit=u'')
    Ingredients213 = Ingredients(amount=u'600',name = u'frozen peas',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients214 = Ingredients(amount=u'250',name = u'ricotta',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'g')
    Ingredients215 = Ingredients(amount=u'4',name = u'extra-virgin olive oil',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'tbsp')
    Ingredients216 = Ingredients(amount=u'15',name = u'chives',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients217 = Ingredients(amount=u'30',name = u'mint',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'g')
    Ingredients218 = Ingredients(amount=u'1',name = u'lemon',is_vegetarian=1,is_vegan=1,is_gluten_free=1,unit=u'')
    Ingredients219 = Ingredients(amount=u'',name = u'vegetarian hard cheese',is_vegetarian=1,is_vegan=0,is_gluten_free=1,unit=u'')
    
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    Recipe1.ingredients.append(Ingredients1)
    
    Recipe2.ingredients.append(Ingredients3)
    Recipe2.ingredients.append(Ingredients4)
    Recipe2.ingredients.append(Ingredients5)
    Recipe2.ingredients.append(Ingredients6)
    Recipe2.ingredients.append(Ingredients7)
    Recipe2.ingredients.append(Ingredients8)
    Recipe2.ingredients.append(Ingredients9)
    Recipe2.ingredients.append(Ingredients10)
    Recipe2.ingredients.append(Ingredients11)
    Recipe2.ingredients.append(Ingredients12)
    
    Recipe3.ingredients.append(Ingredients13)
    Recipe3.ingredients.append(Ingredients14)
    Recipe3.ingredients.append(Ingredients15)
    Recipe3.ingredients.append(Ingredients16)
    Recipe3.ingredients.append(Ingredients17)
    
    Recipe4.ingredients.append(Ingredients18)
    Recipe4.ingredients.append(Ingredients19)
    Recipe4.ingredients.append(Ingredients20)
    Recipe4.ingredients.append(Ingredients21)
    Recipe4.ingredients.append(Ingredients22)
    Recipe4.ingredients.append(Ingredients23)
    Recipe4.ingredients.append(Ingredients24)
    Recipe4.ingredients.append(Ingredients25)
    
    Recipe5.ingredients.append(Ingredients26)
    Recipe5.ingredients.append(Ingredients27)
    Recipe5.ingredients.append(Ingredients28)
    Recipe5.ingredients.append(Ingredients29)
    Recipe5.ingredients.append(Ingredients30)
    Recipe5.ingredients.append(Ingredients31)
    Recipe5.ingredients.append(Ingredients32)
    Recipe5.ingredients.append(Ingredients33)
    Recipe5.ingredients.append(Ingredients34)
    
    Recipe6.ingredients.append(Ingredients35)
    Recipe6.ingredients.append(Ingredients36)
    Recipe6.ingredients.append(Ingredients37)
    Recipe6.ingredients.append(Ingredients38)
    Recipe6.ingredients.append(Ingredients39)
    Recipe6.ingredients.append(Ingredients40)
    
    Recipe7.ingredients.append(Ingredients41)
    Recipe7.ingredients.append(Ingredients42)
    Recipe7.ingredients.append(Ingredients43)
    Recipe7.ingredients.append(Ingredients44)
    Recipe7.ingredients.append(Ingredients45)
    Recipe7.ingredients.append(Ingredients46)
    Recipe7.ingredients.append(Ingredients47)
    Recipe7.ingredients.append(Ingredients48)
    Recipe7.ingredients.append(Ingredients49)
    Recipe7.ingredients.append(Ingredients50)
    Recipe7.ingredients.append(Ingredients51)
    
    Recipe8.ingredients.append(Ingredients52)
    Recipe8.ingredients.append(Ingredients53)
    Recipe8.ingredients.append(Ingredients54)
    Recipe8.ingredients.append(Ingredients55)
    Recipe8.ingredients.append(Ingredients56)
    Recipe8.ingredients.append(Ingredients57)
    Recipe8.ingredients.append(Ingredients58)
    Recipe8.ingredients.append(Ingredients59)
    Recipe8.ingredients.append(Ingredients60)
    Recipe8.ingredients.append(Ingredients61)
    
    Recipe9.ingredients.append(Ingredients62)
    Recipe9.ingredients.append(Ingredients63)
    Recipe9.ingredients.append(Ingredients64)
    Recipe9.ingredients.append(Ingredients65)
    Recipe9.ingredients.append(Ingredients66)
    Recipe9.ingredients.append(Ingredients67)
    Recipe9.ingredients.append(Ingredients68)
    Recipe9.ingredients.append(Ingredients69)
    
    Recipe10.ingredients.append(Ingredients70)
    Recipe10.ingredients.append(Ingredients71)
    Recipe10.ingredients.append(Ingredients72)
    Recipe10.ingredients.append(Ingredients73)
    Recipe10.ingredients.append(Ingredients74)
    Recipe10.ingredients.append(Ingredients75)
    Recipe10.ingredients.append(Ingredients76)
    Recipe10.ingredients.append(Ingredients77)
    Recipe10.ingredients.append(Ingredients78)
    Recipe10.ingredients.append(Ingredients79)
    
    Recipe11.ingredients.append(Ingredients80)
    Recipe11.ingredients.append(Ingredients81)
    Recipe11.ingredients.append(Ingredients82)
    Recipe11.ingredients.append(Ingredients83)
    Recipe11.ingredients.append(Ingredients84)
    Recipe11.ingredients.append(Ingredients85)
    Recipe11.ingredients.append(Ingredients86)
    Recipe11.ingredients.append(Ingredients87)
    Recipe11.ingredients.append(Ingredients88)
    Recipe11.ingredients.append(Ingredients89)
    
    Recipe12.ingredients.append(Ingredients90)
    Recipe12.ingredients.append(Ingredients91)
    Recipe12.ingredients.append(Ingredients92)
    Recipe12.ingredients.append(Ingredients93)
    Recipe12.ingredients.append(Ingredients94)
    Recipe12.ingredients.append(Ingredients95)
    Recipe12.ingredients.append(Ingredients96)
    Recipe12.ingredients.append(Ingredients97)
    Recipe12.ingredients.append(Ingredients98)
    Recipe12.ingredients.append(Ingredients99)
    
    Recipe13.ingredients.append(Ingredients100)
    Recipe13.ingredients.append(Ingredients101)
    Recipe13.ingredients.append(Ingredients102)
    Recipe13.ingredients.append(Ingredients103)
    Recipe13.ingredients.append(Ingredients104)
    Recipe13.ingredients.append(Ingredients105)
    Recipe13.ingredients.append(Ingredients106)
    Recipe13.ingredients.append(Ingredients107)
    Recipe13.ingredients.append(Ingredients108)
    Recipe13.ingredients.append(Ingredients109)
    Recipe13.ingredients.append(Ingredients110)
    Recipe13.ingredients.append(Ingredients111)
    Recipe13.ingredients.append(Ingredients112)
    Recipe13.ingredients.append(Ingredients113)
    
    Recipe14.ingredients.append(Ingredients114)
    Recipe14.ingredients.append(Ingredients115)
    Recipe14.ingredients.append(Ingredients116)
    Recipe14.ingredients.append(Ingredients117)
    Recipe14.ingredients.append(Ingredients118)
    
    Recipe15.ingredients.append(Ingredients119)
    Recipe15.ingredients.append(Ingredients120)
    Recipe15.ingredients.append(Ingredients121)
    Recipe15.ingredients.append(Ingredients122)
    Recipe15.ingredients.append(Ingredients123)
    Recipe15.ingredients.append(Ingredients124)
    Recipe15.ingredients.append(Ingredients125)
    Recipe15.ingredients.append(Ingredients126)
    Recipe15.ingredients.append(Ingredients127)
    
    Recipe16.ingredients.append(Ingredients128)
    Recipe16.ingredients.append(Ingredients129)
    Recipe16.ingredients.append(Ingredients130)
    Recipe16.ingredients.append(Ingredients131)
    Recipe16.ingredients.append(Ingredients132)
    Recipe16.ingredients.append(Ingredients133)
    Recipe16.ingredients.append(Ingredients134)
    Recipe16.ingredients.append(Ingredients135)
    Recipe16.ingredients.append(Ingredients136)
    Recipe16.ingredients.append(Ingredients137)
    Recipe16.ingredients.append(Ingredients138)
    
    Recipe17.ingredients.append(Ingredients139)
    Recipe17.ingredients.append(Ingredients140)
    Recipe17.ingredients.append(Ingredients141)
    Recipe17.ingredients.append(Ingredients142)
    Recipe17.ingredients.append(Ingredients143)
    Recipe17.ingredients.append(Ingredients144)
    Recipe17.ingredients.append(Ingredients145)
    Recipe17.ingredients.append(Ingredients146)
    Recipe17.ingredients.append(Ingredients147)
    Recipe17.ingredients.append(Ingredients148)
    Recipe17.ingredients.append(Ingredients149)
    Recipe17.ingredients.append(Ingredients150)
    
    Recipe18.ingredients.append(Ingredients151)
    Recipe18.ingredients.append(Ingredients152)
    Recipe18.ingredients.append(Ingredients153)
    Recipe18.ingredients.append(Ingredients154)
    Recipe18.ingredients.append(Ingredients155)
    Recipe18.ingredients.append(Ingredients156)
    
    Recipe19.ingredients.append(Ingredients157)
    Recipe19.ingredients.append(Ingredients158)
    Recipe19.ingredients.append(Ingredients159)
    Recipe19.ingredients.append(Ingredients160)
    Recipe19.ingredients.append(Ingredients161)
    Recipe19.ingredients.append(Ingredients162)
    Recipe19.ingredients.append(Ingredients163)
    Recipe19.ingredients.append(Ingredients164)
    Recipe19.ingredients.append(Ingredients165)
    Recipe19.ingredients.append(Ingredients166)
    
    Recipe20.ingredients.append(Ingredients167)
    Recipe20.ingredients.append(Ingredients168)
    Recipe20.ingredients.append(Ingredients169)
    Recipe20.ingredients.append(Ingredients170)
    Recipe20.ingredients.append(Ingredients171)
    
    Recipe21.ingredients.append(Ingredients172)
    Recipe21.ingredients.append(Ingredients173)
    Recipe21.ingredients.append(Ingredients174)
    Recipe21.ingredients.append(Ingredients175)
    Recipe21.ingredients.append(Ingredients176)
    Recipe21.ingredients.append(Ingredients177)
    Recipe21.ingredients.append(Ingredients178)
    Recipe21.ingredients.append(Ingredients179)
    Recipe21.ingredients.append(Ingredients180)
    Recipe21.ingredients.append(Ingredients181)
    
    Recipe22.ingredients.append(Ingredients182)
    Recipe22.ingredients.append(Ingredients183)
    Recipe22.ingredients.append(Ingredients184)
    Recipe22.ingredients.append(Ingredients185)
    Recipe22.ingredients.append(Ingredients186)
    Recipe22.ingredients.append(Ingredients187)
    Recipe22.ingredients.append(Ingredients188)
    Recipe22.ingredients.append(Ingredients189)
    Recipe22.ingredients.append(Ingredients190)
    Recipe22.ingredients.append(Ingredients191)
    
    Recipe23.ingredients.append(Ingredients192)
    Recipe23.ingredients.append(Ingredients193)
    Recipe23.ingredients.append(Ingredients194)
    Recipe23.ingredients.append(Ingredients195)
    Recipe23.ingredients.append(Ingredients196)
    
    Recipe24.ingredients.append(Ingredients197)
    Recipe24.ingredients.append(Ingredients198)
    Recipe24.ingredients.append(Ingredients199)
    Recipe24.ingredients.append(Ingredients200)
    Recipe24.ingredients.append(Ingredients201)
    Recipe24.ingredients.append(Ingredients202)
    Recipe24.ingredients.append(Ingredients203)
    Recipe24.ingredients.append(Ingredients204)
    Recipe24.ingredients.append(Ingredients205)
    Recipe24.ingredients.append(Ingredients206)
    Recipe24.ingredients.append(Ingredients207)
    Recipe24.ingredients.append(Ingredients208)
    Recipe24.ingredients.append(Ingredients209)
    
    Recipe25.ingredients.append(Ingredients210)
    Recipe25.ingredients.append(Ingredients211)
    Recipe25.ingredients.append(Ingredients212)
    Recipe25.ingredients.append(Ingredients213)
    Recipe25.ingredients.append(Ingredients214)
    Recipe25.ingredients.append(Ingredients215)
    Recipe25.ingredients.append(Ingredients216)
    Recipe25.ingredients.append(Ingredients217)
    Recipe25.ingredients.append(Ingredients218)
    Recipe25.ingredients.append(Ingredients219)
    
    db.session.add(Recipe1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Ingredients1)
    db.session.add(Recipe2)
    db.session.add(Ingredients3)
    db.session.add(Ingredients4)
    db.session.add(Ingredients5)
    db.session.add(Ingredients6)
    db.session.add(Ingredients7)
    db.session.add(Ingredients8)
    db.session.add(Ingredients9)
    db.session.add(Ingredients10)
    db.session.add(Ingredients11)
    db.session.add(Ingredients12)
    db.session.add(Recipe3)
    db.session.add(Ingredients13)
    db.session.add(Ingredients14)
    db.session.add(Ingredients15)
    db.session.add(Ingredients16)
    db.session.add(Ingredients17)
    db.session.add(Recipe4)
    db.session.add(Ingredients18)
    db.session.add(Ingredients19)
    db.session.add(Ingredients20)
    db.session.add(Ingredients21)
    db.session.add(Ingredients22)
    db.session.add(Ingredients23)
    db.session.add(Ingredients24)
    db.session.add(Ingredients25)
    db.session.add(Recipe5)
    db.session.add(Ingredients26)
    db.session.add(Ingredients27)
    db.session.add(Ingredients28)
    db.session.add(Ingredients29)
    db.session.add(Ingredients30)
    db.session.add(Ingredients31)
    db.session.add(Ingredients32)
    db.session.add(Ingredients33)
    db.session.add(Ingredients34)
    db.session.add(Recipe6)
    db.session.add(Ingredients35)
    db.session.add(Ingredients36)
    db.session.add(Ingredients37)
    db.session.add(Ingredients38)
    db.session.add(Ingredients39)
    db.session.add(Ingredients40)
    db.session.add(Recipe7)
    db.session.add(Ingredients41)
    db.session.add(Ingredients42)
    db.session.add(Ingredients43)
    db.session.add(Ingredients44)
    db.session.add(Ingredients45)
    db.session.add(Ingredients46)
    db.session.add(Ingredients47)
    db.session.add(Ingredients48)
    db.session.add(Ingredients49)
    db.session.add(Ingredients50)
    db.session.add(Ingredients51)
    db.session.add(Recipe8)
    db.session.add(Ingredients52)
    db.session.add(Ingredients53)
    db.session.add(Ingredients54)
    db.session.add(Ingredients55)
    db.session.add(Ingredients56)
    db.session.add(Ingredients57)
    db.session.add(Ingredients58)
    db.session.add(Ingredients59)
    db.session.add(Ingredients60)
    db.session.add(Ingredients61)
    db.session.add(Recipe9)
    db.session.add(Ingredients62)
    db.session.add(Ingredients63)
    db.session.add(Ingredients64)
    db.session.add(Ingredients65)
    db.session.add(Ingredients66)
    db.session.add(Ingredients67)
    db.session.add(Ingredients68)
    db.session.add(Ingredients69)
    db.session.add(Recipe10)
    db.session.add(Ingredients70)
    db.session.add(Ingredients71)
    db.session.add(Ingredients72)
    db.session.add(Ingredients73)
    db.session.add(Ingredients74)
    db.session.add(Ingredients75)
    db.session.add(Ingredients76)
    db.session.add(Ingredients77)
    db.session.add(Ingredients78)
    db.session.add(Ingredients79)
    db.session.add(Recipe11)
    db.session.add(Ingredients80)
    db.session.add(Ingredients81)
    db.session.add(Ingredients82)
    db.session.add(Ingredients83)
    db.session.add(Ingredients84)
    db.session.add(Ingredients85)
    db.session.add(Ingredients86)
    db.session.add(Ingredients87)
    db.session.add(Ingredients88)
    db.session.add(Ingredients89)
    db.session.add(Recipe12)
    db.session.add(Ingredients90)
    db.session.add(Ingredients91)
    db.session.add(Ingredients92)
    db.session.add(Ingredients93)
    db.session.add(Ingredients94)
    db.session.add(Ingredients95)
    db.session.add(Ingredients96)
    db.session.add(Ingredients97)
    db.session.add(Ingredients98)
    db.session.add(Ingredients99)
    db.session.add(Recipe13)
    db.session.add(Ingredients100)
    db.session.add(Ingredients101)
    db.session.add(Ingredients102)
    db.session.add(Ingredients103)
    db.session.add(Ingredients104)
    db.session.add(Ingredients105)
    db.session.add(Ingredients106)
    db.session.add(Ingredients107)
    db.session.add(Ingredients108)
    db.session.add(Ingredients109)
    db.session.add(Ingredients110)
    db.session.add(Ingredients111)
    db.session.add(Ingredients112)
    db.session.add(Ingredients113)
    db.session.add(Recipe14)
    db.session.add(Ingredients114)
    db.session.add(Ingredients115)
    db.session.add(Ingredients116)
    db.session.add(Ingredients117)
    db.session.add(Ingredients118)
    db.session.add(Recipe15)
    db.session.add(Ingredients119)
    db.session.add(Ingredients120)
    db.session.add(Ingredients121)
    db.session.add(Ingredients122)
    db.session.add(Ingredients123)
    db.session.add(Ingredients124)
    db.session.add(Ingredients125)
    db.session.add(Ingredients126)
    db.session.add(Ingredients127)
    db.session.add(Recipe16)
    db.session.add(Ingredients128)
    db.session.add(Ingredients129)
    db.session.add(Ingredients130)
    db.session.add(Ingredients131)
    db.session.add(Ingredients132)
    db.session.add(Ingredients133)
    db.session.add(Ingredients134)
    db.session.add(Ingredients135)
    db.session.add(Ingredients136)
    db.session.add(Ingredients137)
    db.session.add(Ingredients138)
    db.session.add(Recipe17)
    db.session.add(Ingredients139)
    db.session.add(Ingredients140)
    db.session.add(Ingredients141)
    db.session.add(Ingredients142)
    db.session.add(Ingredients143)
    db.session.add(Ingredients144)
    db.session.add(Ingredients145)
    db.session.add(Ingredients146)
    db.session.add(Ingredients147)
    db.session.add(Ingredients148)
    db.session.add(Ingredients149)
    db.session.add(Ingredients150)
    db.session.add(Recipe18)
    db.session.add(Ingredients151)
    db.session.add(Ingredients152)
    db.session.add(Ingredients153)
    db.session.add(Ingredients154)
    db.session.add(Ingredients155)
    db.session.add(Ingredients156)
    db.session.add(Recipe19)
    db.session.add(Ingredients157)
    db.session.add(Ingredients158)
    db.session.add(Ingredients159)
    db.session.add(Ingredients160)
    db.session.add(Ingredients161)
    db.session.add(Ingredients162)
    db.session.add(Ingredients163)
    db.session.add(Ingredients164)
    db.session.add(Ingredients165)
    db.session.add(Ingredients166)
    db.session.add(Recipe20)
    db.session.add(Ingredients167)
    db.session.add(Ingredients168)
    db.session.add(Ingredients169)
    db.session.add(Ingredients170)
    db.session.add(Ingredients171)
    db.session.add(Recipe21)
    db.session.add(Ingredients172)
    db.session.add(Ingredients173)
    db.session.add(Ingredients174)
    db.session.add(Ingredients175)
    db.session.add(Ingredients176)
    db.session.add(Ingredients177)
    db.session.add(Ingredients178)
    db.session.add(Ingredients179)
    db.session.add(Ingredients180)
    db.session.add(Ingredients181)
    db.session.add(Recipe22)
    db.session.add(Ingredients182)
    db.session.add(Ingredients183)
    db.session.add(Ingredients184)
    db.session.add(Ingredients185)
    db.session.add(Ingredients186)
    db.session.add(Ingredients187)
    db.session.add(Ingredients188)
    db.session.add(Ingredients189)
    db.session.add(Ingredients190)
    db.session.add(Ingredients191)
    db.session.add(Recipe23)
    db.session.add(Ingredients192)
    db.session.add(Ingredients193)
    db.session.add(Ingredients194)
    db.session.add(Ingredients195)
    db.session.add(Ingredients196)
    db.session.add(Recipe24)
    db.session.add(Ingredients197)
    db.session.add(Ingredients198)
    db.session.add(Ingredients199)
    db.session.add(Ingredients200)
    db.session.add(Ingredients201)
    db.session.add(Ingredients202)
    db.session.add(Ingredients203)
    db.session.add(Ingredients204)
    db.session.add(Ingredients205)
    db.session.add(Ingredients206)
    db.session.add(Ingredients207)
    db.session.add(Ingredients208)
    db.session.add(Ingredients209)
    db.session.add(Recipe25)
    db.session.add(Ingredients210)
    db.session.add(Ingredients211)
    db.session.add(Ingredients212)
    db.session.add(Ingredients213)
    db.session.add(Ingredients214)
    db.session.add(Ingredients215)
    db.session.add(Ingredients216)
    db.session.add(Ingredients217)
    db.session.add(Ingredients218)
    db.session.add(Ingredients219)
    
    
    db.session.commit()
    
    
    return redirect(url_for('login'))
    
# Change debug mode
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
            
# add 404 for missing queries http://flask-sqlalchemy.pocoo.org/2.3/queries/#queries-in-views