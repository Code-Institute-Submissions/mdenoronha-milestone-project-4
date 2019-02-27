from flask import Flask, render_template, redirect, request, url_for, send_file, session
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

s3 = FlaskS3(app)
db = SQLAlchemy(app)

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
    name = db.Column(db.String(80), unique=True, nullable=False)
    unit = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
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

    def __repr__(self):
        return '<User %r>' % self.username
    
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
        recipe_dict.update({recipe.name:recipe.id})
    # https://stackoverflow.com/questions/19884900/how-to-pass-dictionary-from-jinja2-using-python-to-javascript
    recipe_object = (json.dumps(recipe_dict)
    .replace(u'<', u'\\u003c')
    .replace(u'>', u'\\u003e')
    .replace(u'&', u'\\u0026')
    .replace(u"'", u'\\u0027'))
    
    # Altering the homepage 
    featured_recipes_ids = [1,2,3]
    vegan_recipes_ids = [4,5,6,7]
    featured_recipes = []
    vegan_recipes = []
    
    for recipe in featured_recipes_ids:
        temp_recipe = Recipe.query.filter_by(id=recipe).first()
        featured_recipes.append(temp_recipe)
    for recipe in vegan_recipes_ids:
        temp_recipe = Recipe.query.filter_by(id=recipe).first()
        vegan_recipes.append(temp_recipe)
        
    
    return render_template('index.html',recipe_object=recipe_object, featured_recipes=featured_recipes, vegan_recipes=vegan_recipes)
    
@app.route('/add-recipe', methods=['POST', 'GET'])
def add_recipe():
    
    if request.method == 'POST':
        
        name = request.form['dish_name']
        serves = request.form['serves']
        difficulty = request.form['difficulty']
        time = request.form['time']
        method = request.form['method']
        recipe_picture = request.files['inputFile']
        image_file_url = save_profile_picture(recipe_picture)
        
        temp_recipe = Recipe(name=name,image_file=image_file_url,serves = serves,difficulty=difficulty,time=time,views = 0,method = method,user_id = 1)
        db.session.add(temp_recipe)
        db.session.commit()
    # db.create_all()
    
    # file = request.files['inputFile']
    # newFile = Filecontents(name=file.filename, data=file.read())
    # db.session.add(newFile)
    # db.session.commit()
    
    return render_template('upload.html')
    
@app.route('/recipe/<recipe_name>/<recipe_id>')
def recipe(recipe_name, recipe_id):
    
    recipe_result = Recipe.query.filter_by(id=recipe_id).first()
    
    return render_template('recipe.html', recipe_result=recipe_result)
    
    
@app.route('/search', methods=['POST', 'GET'])
def search():
    
    result = None
    if request.method == "POST":
        search_term = request.form["search"] 
        recipe_type = request.form.getlist('recipe-type')

        # test = Recipe.query.filter(~Recipe.ingredients.any(Ingredients.is_vegan == True))
        # Check to see if returned recipes have nutritional requirements
        if not recipe_type:
            checkboxes = [None, None, None]
            result = (Recipe.query
            .filter(Recipe.name.contains(search_term))
            .order_by(Recipe.views.desc()))
        elif "vegan" in recipe_type and "gluten-free" in recipe_type:
            checkboxes = ["vegan", "vegetarian", "gluten_free"]
            result = (Recipe.query
            .filter(Recipe.name.contains(search_term))
            .filter(~Recipe.ingredients.any(Ingredients.is_vegan == False))
            .filter(~Recipe.ingredients.any(Ingredients.is_vegetarian == False))
            .filter(~Recipe.ingredients.any(Ingredients.is_gluten_free == False))
            .order_by(Recipe.views.desc()))
        elif "vegan" in recipe_type:
            checkboxes = ["vegan", "vegetarian", None]
            result = (Recipe.query
            .filter(Recipe.name.contains(search_term))
            .filter(~Recipe.ingredients.any(Ingredients.is_vegan == False))
            .filter(~Recipe.ingredients.any(Ingredients.is_vegetarian == False))
            .order_by(Recipe.views.desc()))
        elif "vegetarian" in recipe_type and "gluten-free" in recipe_type:
            checkboxes = [None, "vegetarian", "gluten_free"]
            result = (Recipe.query
            .filter(Recipe.name.contains(search_term))
            .filter(~Recipe.ingredients.any(Ingredients.is_vegetarian == False))
            .filter(~Recipe.ingredients.any(Ingredients.is_gluten_free == False))
            .order_by(Recipe.views.desc()))
        elif "vegetarian" in recipe_type:
            checkboxes = [None, "vegetarian", None]
            result = (Recipe.query
            .filter(Recipe.name.contains(search_term))
            .filter(~Recipe.ingredients.any(Ingredients.is_vegetarian == False))
            .order_by(Recipe.views.desc()))
        elif "gluten-free" in recipe_type:
            checkboxes = [None, None, "gluten_free"]
            result = (Recipe.query
            .filter(Recipe.name.contains(search_term))
            .filter(~Recipe.ingredients.any(Ingredients.is_gluten_free == False))
            .order_by(Recipe.views.desc()))

    return render_template('search.html', result=result, checkboxes=checkboxes, search_term=search_term)
    
@app.route('/register', methods=['POST', 'GET'])
def register():
    
    
    return render_template('register.html')
    
@app.route('/register_user', methods=['POST', 'GET'])
def register_user():
    
    first_name = request.form["first_name"] 
    last_name = request.form["last_name"] 
    username = request.form["username"]
    password = request.form["password"] 
    user = User(first_name=first_name,last_name=last_name, username=username,password = password)
    db.session.add(user)
    db.session.commit()
    
    session["username"] = username
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
            
# add 404 for missing queries http://flask-sqlalchemy.pocoo.org/2.3/queries/#queries-in-views