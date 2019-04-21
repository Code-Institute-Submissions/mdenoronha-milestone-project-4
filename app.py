from flask import Flask, render_template, redirect, request, url_for, send_file, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
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
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

s3 = FlaskS3(app)
db = SQLAlchemy(app)


# Create list of paginated pages with active number in middle where possible
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
        else:
            if page + counter - 2 > 0 and page + counter - 2 < total_pages:
                pagination_num.append(int(page + counter - 2))
    
    return pagination_num

# Returns recipes from db filtered using search term and recipes filters   
def return_search(filters, search_term, page):

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
    
"""
Check to see if uploaded file type is in ALLOWED_EXTENSIONS
Assistance from Flask documentation at
http://flask.pocoo.org/docs/1.0/patterns/fileuploads/
"""

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    
"""
Takes recipe image file, renames with random string and adds to S3 bucket
Assistance for function provided by CI tutor
"""

def save_profile_picture(form_picture):          
    random_hex = ''.join([random.choice(string.digits) for n in range(8)])    
    _, f_ext = os.path.splitext(form_picture.filename)  
    picture_fn = random_hex + f_ext
    s3 = boto3.resource('s3')
    s3.Bucket('recipe-db').put_object(Key="static/recipe_images/" + picture_fn, Body=form_picture)
    
    return picture_fn 
    
def add_ingredients_to_dict():
    
    added_recipe_ingredients = {}
        
    for counter, (ingred, amount) in enumerate(zip(request.form.getlist('ingredient'), request.form.getlist('amount'))):
            
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
        
        added_recipe_ingredients[counter] = temp_ingred
            
    return added_recipe_ingredients
    
def return_allergy_info(recipes):
    
    allergy_info = {}
    
    for res in recipes:
        temp_allergy = {}
        for allergy in allergies:
            # Returns boolean for allergy restrictive status of ingredients
            allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = False))' % (res.id, allergy)).fetchall()
            temp_allergy[allergy] = allergy_res[0][0]
        allergy_info[res.id] = temp_allergy
        
    return allergy_info
    
def session_check():
    if not session:
        return True
        
    if not 'username' in session:
        return True
    
    return False

default_filter_dict = {
            'difficulty_type': [u'easy', u'medium', u'hard'], 
            'recipe_type': [], 
            'time': [u'10', u'180'], 
            'serves': [u'1', u'6'], 
            'ingredients': []
        }
        
allergies = ['is_gluten_free','is_vegan','is_vegetarian']

# Table for recipes and relevant ingredients
recipe_ingredients = db.Table('recipe_ingredients',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id')),
    db.Column('ingredients_id', db.Integer, db.ForeignKey('ingredients.id')),
)

# Table for recipes and users who have viewed
viewed_recipes = db.Table('viewed_recipes',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id')),
    # Change to user_id when database is updated
    db.Column('user_ud', db.Integer, db.ForeignKey('user.id')),
)

# Table for recipes
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
  
# Table for ingredients  
class Ingredients(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.String(80), nullable=False)
    is_vegetarian = db.Column(db.Boolean, nullable=False)
    is_vegan = db.Column(db.Boolean, nullable=False)
    is_gluten_free = db.Column(db.Boolean, nullable=False)
    
    def __repr__(self):
        return '<Ingredients %r>' % self.name

# Table for users   
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

"""
Applies default filters to session with additional custom recipe_type filter. 
Used when linking to a search page with specific recipes filtered (e.g. all vegan)
"""

@app.route('/auto-search/<filter_to_add>')
def auto_search(filter_to_add):
    # Sets user search filters to default (with url parameter as recipe type)
    default_filter_dict["recipe_type"] = [filter_to_add]
    session["filters"] = default_filter_dict
    
    session["search_term"] = ""
    
    return redirect(url_for('search_get'))

@app.route('/search', methods=["POST"])
def search_post():
    
    search_term = request.form["search"] 
    session["search_term"] = search_term
    
    page = request.args.get('page', 1, type=int)
    
    filters = {}
    # Get form data for search filter
    try:
        recipe_type = request.form.getlist('recipe-type')
        difficulty_type = request.form.getlist('difficulty-type')
        serves_value = request.form["serves-value"]
        time_value = request.form["time-value"]
        ingredients_value = request.form["ingredients-value"].lower()
    except KeyError:
        # If error, reset to default search
        recipe_type = []
        difficulty_type = [u'easy', u'medium', u'hard']
        serves_value = "1,6"
        time_value = "10,180"
        ingredients_value = ""
        
    # Take Ingredients from form and apply to filters dict 
    if not ingredients_value:
        filters["ingredients"] = []
    else:
        ingredients_value_list = [ingredients_value][0].split(',')
        filters["ingredients"] = ingredients_value_list
    
    # Take Serves from form and apply to filters dict 
    serves_value_list = [serves_value][0].split(',')
    filters["serves"] = serves_value_list
    
    # Take Time from form and apply to filters dict 
    time_value_list = [time_value][0].split(',')
    filters["time"] = time_value_list
    
    # Recipe type and difficulty
    recipe_type_list = []
    difficulty_list = []
    
    # Take Recipe_type from form and apply to filters dict 
    for r in recipe_type:
        recipe_type_list.append(r)
    # If there is no recipe_type, session will show as empty
    filters["recipe_type"] = recipe_type_list
    
    # Take Difficulty from form and apply to filters dict 
    for difficulty in difficulty_type:
        difficulty_list.append(difficulty)
    # If there is no recipe_type, session will show as empty
    filters["difficulty_type"] = difficulty_list
    
    # Apply all filters to session
    session["filters"] = filters

    
    return redirect(url_for('search_get'))

# Split into Post/Redirect/Get to remove Confirm Form Submission message
@app.route('/search', methods=["GET"])
def search_get():
    
    # Find current page to aid with pagination
    page = request.args.get('page', 1, type=int)
    
    # If session doesn't contain filter, reset to default
    if "filters" not in session:
        session["filters"] = default_filter_dict
    
    # If session doesn't contain search term, reset to no search
    if not "search_term" in session:
        session["search_term"] = ""
    search_term = session["search_term"]
    
    # Return records from the database
    result = return_search(session["filters"], session["search_term"], page)
    
    # Find total pages and pagination numbers from result object
    total_pages = result.pages
    pagination_num = create_pagination_num(total_pages, page)
    
    """
    Loop through each result and find relational ingredients records - to identify
    if the record meets allergy requirements.
    """
        
    allergies = ['is_gluten_free','is_vegan','is_vegetarian']
    allergy_info = {}
    
    allergy_info = return_allergy_info(result.items)
        
    # Page title
    title = "Search Recipes: %s" % search_term
    
    return render_template('search.html', allergy_info=allergy_info, result=result, search_term=search_term, pagination_num=pagination_num, page=page, title=title) 
    
@app.route('/')
def index():
    
    # Working with ResultProxy assistance from https://kite.com/python/docs/sqlalchemy.engine.result.ResultProxy
    
    """
    Returns top 20 recipes by view count and adds to dict ready to input into
    page for javascript to retrieve
    """
    top_recipes = Recipe.query.order_by(Recipe.views.desc()).limit(20).all()
    recipe_dict = {}
    for recipe in top_recipes:
        recipe_dict.update({recipe.name: recipe.id})
    """
    Assistance on passing Python dictionary to javascrip from 
    https://stackoverflow.com/questions/19884900/how-to-pass-dictionary-from-jinja2-using-python-to-javascript
    """
    recipe_object = (json.dumps(recipe_dict)
    .replace(u'<', u'\\u003c')
    .replace(u'>', u'\\u003e')
    .replace(u'&', u'\\u0026')
    .replace(u"'", u'\\u0027'))

    featured_recipes = []
    allergy_info = {}
    
    # Returns top 4 recipes to be featured on homepage
    featured_recipes = Recipe.query.order_by(Recipe.views.desc()).limit(4).all()
    
    """
    Loop through each result and find relational ingredients records - to identify
    if the record meets allergy requirements.
    """
        
    allergy_info = return_allergy_info(featured_recipes)
            
    return render_template('index.html',recipe_object=recipe_object, featured_recipes=featured_recipes, allergy_info=allergy_info, title="Worldwide Recipes | Home")
    
@app.route('/delete/<recipe_id>')
def delete_recipe(recipe_id):
    
    if session_check():
        return redirect(url_for('index'))
    
    # Check if recipe belongs to user
    user = User.query.filter_by(username=session["username"]).first()
    
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    
    if user.id != recipe.user_id:
        flash("You may only delete recipes you own")
        return redirect(url_for('account_my_recipes'))
    
    # Deletes recipe record
    Recipe.query.filter_by(id=recipe_id).delete()
    
    db.session.commit()
    
    # Deletes associated ingredients
    delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
    db.engine.execute(delete_str)
    
    flash("Recipe deleted successfully")
    return redirect(url_for('account_my_recipes'))
    
@app.route('/add-recipe/info', methods=['POST', 'GET'])
def add_recipe_info():
    
    # Check if user is logged in
    if session_check():
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        # Retrieves images from form
        recipe_picture = request.files['inputFile']
        
        # Check to ensure file is supported filetype
        if not allowed_file(recipe_picture.filename):
            flash("Uploaded files can only be .jpeg .jpg or .png format")
            return redirect(url_for('add_recipe_info'))
        
        # Check to see if recipe name has been added before
        same_name_result = Recipe.query.filter(func.lower(Recipe.name) == func.lower(request.form['dish_name'])).first()
        if same_name_result:
            flash("A recipe by this name has already been created")
            return redirect(url_for('add_recipe_info'))
        
        # Images added to AWS bucket
        image_file_url = save_profile_picture(recipe_picture)
        
        # Recipe info added to session
        session["added_recipe"] = {
            'name': request.form['dish_name'],
            'serves': request.form['serves'],
            'difficulty': request.form['difficulty'],
            'time': request.form['time'],
            'method': request.form['method'],
            'image_file_url': image_file_url
        }
        
        return redirect(url_for('add_recipe_ingredients'))
        
    return render_template('upload.html', title="Add Recipe | Info")

@app.route('/update-recipe/info/<recipe_id>', methods=['POST', 'GET'])
def update_recipe_info(recipe_id):
    
    # Check is user is logged in
    if session_check():
        flash("Please login to update recipes")
        return redirect(url_for('register'))
    
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    user = User.query.filter_by(username=session["username"]).first()
    
    # Check to see if recipe belongs to user
    if recipe.user_id != user.id:
        flash("This recipe can only be edited by its author")
        return redirect(url_for('index'))
        
    if request.method == "POST":
        # Check if a new image was submitted, if not the original image is used
        try:
            request.files['inputFile']
        except KeyError:
            image_file_url = recipe.image_file
        else:
            recipe_picture = request.files['inputFile']
            
            # Check if image is allowed filetype
            if not allowed_file(recipe_picture.filename):
                
                flash("Uploaded files can only be .jpeg .jpg or .png format")
                return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
            # Images added to AWS bucket
            image_file_url = save_profile_picture(recipe_picture)
            
        
        # Check to see if recipe name has been added before
        same_name_result = Recipe.query.filter(func.lower(Recipe.name) == func.lower(request.form['dish_name'])).first()
        if same_name_result and int(same_name_result.id) != int(recipe_id):
            flash("A recipe by this name has already been created")
            return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
        
        # Updated recipe info added to session
        session["update_recipe"] = {
            'name': request.form['dish_name'],
            'serves': request.form['serves'],
            'difficulty': request.form['difficulty'],
            'time': request.form['time'],
            'method': request.form['method'],
            'image_file_url': image_file_url
        }
    
        return redirect(url_for('update_recipe_ingredients', recipe_id=recipe_id))
    
    return render_template('update.html', recipe=recipe, title="Update Recipe | Info")
    
@app.route('/add-recipe/ingredients', methods=['POST', 'GET'])
def add_recipe_ingredients():
    
    # Check if user is logged in
    if session_check():
        return redirect(url_for('register'))
        
    # Check to see if user has submitted recipe info, redirect to previous step if not
    if "added_recipe" not in session:
        return redirect(url_for('add_recipe_info'))
       
    if request.method == "POST":
        # Adds all ingredients submitted in form to session
        session["added_recipe_ingredients"] = add_ingredients_to_dict()
        
        return redirect(url_for('add_recipe_submit'))
    
    return render_template('upload_ingred.html', title="Add Recipe | Ingredients")

@app.route('/update-recipe/ingredients/<recipe_id>', methods=['POST', 'GET'])  
def update_recipe_ingredients(recipe_id):
    # Check if user is logged in
    if session_check():
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    # Check to see if user has submitted recipe info, redirect to previous step if not
    if "update_recipe" not in session:
        return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
    
    user = User.query.filter_by(username=session["username"]).first()
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    
    # Check if recipe belongs to user
    if recipe.user_id != user.id:
        flash("This recipe can only be edited by its author")
        return redirect(url_for('index'))
    
    # Retrieves all relational records from Ingredients to populate form
    search_str = "SELECT * FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
    all_ingreds_id = db.engine.execute(search_str).fetchall()
    
    all_ingreds = {}
    for counter, (k, v) in enumerate(all_ingreds_id):

        all_ingreds[counter] = Ingredients.query.filter_by(id=v).first()
    
    if request.method == "POST":
        
        # Adds all ingredients submitted in form to session
        session["update_recipe_ingredients"] = add_ingredients_to_dict()
    
        return redirect(url_for('update_recipe_submit', recipe_id=recipe_id))
    
    return render_template('update_ingred.html', all_ingreds=all_ingreds, recipe_id=recipe_id, title="Update Recipe | Ingredients")

@app.route('/add-recipe/submit', methods=['POST', 'GET'])
def add_recipe_submit():
    # Check if user is logged in
    if session_check():
        return redirect(url_for('register'))
    
    # Check to see if user has submitted recipe info, redirect to first step if not
    if "added_recipe" not in session:
        return redirect(url_for('add_recipe_info'))
        
    # Check to see if user has submitted recipe ingredients, redirect to previous step if not
    if "added_recipe_ingredients" not in session:
        return redirect(url_for('add_recipe_ingredients'))
    
    # Adds all recipe session data to database model
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
        
        ingreds = Ingredients(name=v["ingred"],
                              is_vegetarian = v["is_vegetarian"],
                              is_vegan=v["is_vegan"],
                              is_gluten_free=v["is_gluten_free"],
                              amount=v["amount"])
                              
        
        
        db.session.add(ingreds)
        temp_recipe.ingredients.append(ingreds)
    

    if request.method == "POST":
        
        # Commits data to database and adds recipe record
        session.pop("added_recipe")
        session.pop("added_recipe_ingredients")
        db.session.commit()
        
        
        flash("Recipe added successfully")
        return redirect(url_for('account_my_recipes'))
        
    
    return render_template('upload_submit.html', allergy_info=allergy_info, added_recipe=added_recipe, added_recipe_ingredients=added_recipe_ingredients, title="Add Recipe | Submit")
    
# Change to update-recipe
@app.route('/update-recipe/submit/<recipe_id>', methods=['POST', 'GET'])
def update_recipe_submit(recipe_id):
    # Check is user is logged in
    if session_check():
        flash("Please login to update recipes")
        return redirect(url_for('register'))
        
    # Check to see if user has updated recipe info, redirect to first step if not
    if "update_recipe" not in session:
        return redirect(url_for('update_recipe_info', recipe_id=recipe_id))

    # Check to see if user has updated recipe ingredients, redirect to previous step if not
    if "update_recipe_ingredients" not in session:
        return redirect(url_for('update_recipe_info', recipe_id=recipe_id))
        
        
    recipe = Recipe.query.filter_by(id=recipe_id).first()
    user = User.query.filter_by(username=session["username"]).first()
    
    # Check to see if recipe belongs to user
    if recipe.user_id != user.id:
        flash("This recipe can only be edited by its author")
        return redirect(url_for('index'))
    
    update_recipe_ingredients = session["update_recipe_ingredients"]
    update_recipe = session["update_recipe"]
                        
    allergy_info = {
        'is_vegan': True,
        'is_vegetarian': True,
        'is_gluten_free': True
    }
    
    # Querys record for view count to display on page
    view_count = Recipe.query.filter_by(id=recipe_id).with_entities(Recipe.views).first()
    view_count = view_count[0]

    for k, v in session["update_recipe_ingredients"].items():
        for allergy in allergy_info:
            if v[allergy] == False:
                allergy_info[allergy] = False
     
    if request.method == "POST":
        
        # Updates record to submitted values
        temp_recipe = Recipe.query.filter_by(id=recipe_id).first()
        temp_recipe.name = session["update_recipe"]["name"]
        temp_recipe.image_file = session["update_recipe"]["image_file_url"]
        temp_recipe.serves = session["update_recipe"]["serves"]
        temp_recipe.difficulty=session["update_recipe"]["difficulty"]
        temp_recipe.time=session["update_recipe"]["time"]
        temp_recipe.method = session["update_recipe"]["method"]
        
        # Deletes all ingredients associated with recipe
        delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
        db.engine.execute(delete_str)
        
        db.session.commit()
        
        # Adds all submitted ingredients
        for counter, (k, v) in enumerate(session["update_recipe_ingredients"].items()):
        
            ingreds = Ingredients(name=v["ingred"],
                              is_vegetarian = v["is_vegetarian"],
                              is_vegan=v["is_vegan"],
                              is_gluten_free=v["is_gluten_free"],
                              amount=v["amount"])
                              
            db.session.add(ingreds)
            temp_recipe.ingredients.append(ingreds)
        
        # Commits to database and updates record
        db.session.commit()
        
        
        session.pop("update_recipe")
        session.pop("update_recipe_ingredients")
        
        flash("Recipe updated successfully")
        return redirect(url_for('account_my_recipes'))
    
    
    return render_template('update_submit.html', view_count=view_count, recipe_id=recipe_id, allergy_info=allergy_info, update_recipe=update_recipe, update_recipe_ingredients=update_recipe_ingredients, title="Update Recipe | Submit")
    
@app.route('/recipe/<recipe_name>/<recipe_id>')
def recipe(recipe_name, recipe_id):
    
    # Retrieves recipe result based on recipe id
    recipe_result = Recipe.query.filter_by(id=recipe_id).first()
    ingredients_result = recipe_result.ingredients.all()
    user = []
    
    if "username" in session:

        user = User.query.filter_by(username=session["username"]).first()
        
        # Checks to see if user has viewed recipe before
        search_str = "SELECT * FROM viewed_recipes WHERE user_ud = %s AND recipe_id = %s ;" % (user.id, recipe_id)
        viewed_recipe = db.engine.execute(search_str).fetchall()
        
        # Adds user to viewed_recipes with recipe id if they haven't viewed it before
        # Recipe view is incremented by one
        if not viewed_recipe:
            user.viewed_recipe.append(recipe_result)
            recipe_result.views = recipe_result.views + 1
            db.session.commit()
    
    # Returns boolean if ingredients of certain allergies are found for recipe
    allergy_info = {}
    
    
    temp_allergy = {}
    for allergy in allergies:
        allergy_res = db.engine.execute('SELECT (NOT EXISTS (SELECT * FROM ingredients INNER JOIN recipe_ingredients on ingredients.id = recipe_ingredients.ingredients_id WHERE recipe_ingredients.recipe_id = %s AND ingredients.%s = False))' % (recipe_result.id, allergy)).fetchall()
        allergy_info[allergy] = allergy_res[0][0]
    
    # Returns list of words used in recipe, excluding filter_words
    filter_words = ["and", "with", "recipe", "on", "the", "&", "side", "of"]
    recipe_result_name_list = (x for x in recipe_result.name.split(' ') if not x in filter_words)
    
    
    related_recipe_result = []
    related_recipe_text = "Related Recipes"
    
    # Returns up to 3 recipes using words in displayed recipe
    for word in recipe_result_name_list:
        temp_related = Recipe.query.filter(Recipe.name.like("%" + word + "%")).filter(Recipe.id != recipe_result.id)
        for temp_result in temp_related:
            if len(related_recipe_result) > 2:
                break
            if not temp_related in related_recipe_result:
                related_recipe_result.append(temp_result)
    
    # If insufficient recipes are found, top 3 recipes are returned
    if len(related_recipe_result) < 2:
        related_recipe_text = "Popular Recipes"
        related_recipe_result = Recipe.query.order_by(Recipe.views.desc()).limit(3)
    
        
    related_allergy_info = return_allergy_info(related_recipe_result)
    
    # Page title
    title = ""
    for word in recipe_result.name.split(' '):
        title += word[0].upper() + word[1:] + " "

    return render_template('recipe.html', user=user, related_recipe_text=related_recipe_text, related_recipe_result=related_recipe_result, related_allergy_info=related_allergy_info, recipe_result=recipe_result, ingredients_result=ingredients_result, allergy_info=allergy_info, title=title)
    
@app.route('/account/my-recipes', methods=['POST', 'GET'])
def account_my_recipes():
    
    # Check to see if user if logged in
    if session_check():
        return redirect(url_for('register'))

    user = User.query.filter_by(username=session['username']).first()
    # Returns all recipes of user
    all_recipes = Recipe.query.filter_by(user_id=user.id).with_entities(Recipe.name, Recipe.id).order_by(Recipe.views.desc()).all()
    
    if request.method == "POST":
        # If submitted password matches password in user record
        if user.password == request.form["current-password"]:
            
            # User record is updated with submitted info
            temp_user = User.query.filter_by(id=user.id).first()
            
            if 'first_name' in request.form:
                temp_user.first_name = request.form['first_name']
            if 'last_name' in request.form:
                temp_user.last_name = request.form["last_name"]
            if 'username' in request.form:
                # Check to see if username has been used previously
                same_username_result = Recipe.query.filter(func.lower(User.username) == func.lower(request.form["username"])).first()
                if same_username_result:
                    flash('An account with the same username already exists')
                    return redirect(url_for('account_my_recipes'))
                temp_user.username = request.form["username"]
                session['username'] = request.form["username"]
            if 'password' in request.form:
                temp_user.password = request.form["password"]
            
            db.session.commit()
        
        else:
            flash("Password incorrect")
    
    return render_template('account_my_recipes.html', all_recipes=all_recipes, user=user, title="My Account")
    
@app.route('/register', methods=['POST', 'GET'])
def register():
    
    # Renders register page
    return render_template('register.html', title="Register")
    
@app.route('/register_user', methods=['POST', 'GET'])
def register_user():
    
    # Retrieves user information from submitted form
    first_name = request.form["first_name"].lower()
    last_name = request.form["last_name"].lower() 
    username = request.form["username"].lower()
    password = request.form["password"].lower()
    
    # Check to see if user by submitted username already exists
    if User.query.filter_by(username=username).count() > 0:
        flash("A user by this username already exists")
        return redirect(url_for('register'))
    else:
        session["username"] = username
        
        # User record added to the database
        user = User(first_name=first_name,last_name=last_name, username=username,password = password)
        db.session.add(user)
        db.session.commit()
        
        flash("User registration successful")
        return redirect(url_for('index'))
    return redirect(url_for('register'))
    
@app.route('/login', methods=['POST', 'GET'])
def login():
    
    # Renders login page
    return render_template('login.html', title="Login")
    
@app.route('/login_user', methods=['POST', 'GET'])
def login_user():
    
    username = request.form["username"].lower()
    password = request.form["password"]
    
    user = User.query.filter_by(username=username).first()
    
    # Check to see if user by submitted username exists
    try:
        user.username
    except AttributeError:
        flash('Incorrect user credentials')
        return redirect(url_for('login'))
    
    # Check to see if submitted password matches user record
    if str(user.password) == str(password):
        session["username"] = username
        flash('Successfully Logged in')
        return redirect(url_for('index'))
    else: 
        flash('Incorrect user credentials')
        return redirect(url_for('login'))
        
@app.route('/logout')
def logout():
    
    # Removes user information from session
    session.clear()
    flash("Log out successful")
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=False)