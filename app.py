from flask import Flask, render_template, redirect, request, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
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
for key in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET_URL'):
    app.config[key] = os.environ[key]

# # Use as env variables
# S3_KEY = "AKIAJKKDQPYOE2GD5PXA"
# S3_SECRET = "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"

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
    # image_file = db.Column(db.Text)
    ingredients = db.relationship('Ingredients', secondary=recipe_ingredients, lazy='subquery',
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
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    recipe = db.relationship('Recipe', backref="author", lazy=True)

    def __repr__(self):
        return '<User %r>' % self.username



# https://www.youtube.com/watch?v=TLgVEBuQURA
class Filecontents(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(300))
    data = db.Column(db.LargeBinary)
    
@app.route('/')
def index():
    
    recipe_names = Recipe.query.all()
    recipe_dict = {}
    for recipe in recipe_names:
        recipe_dict.update({recipe.name:None})
    # https://stackoverflow.com/questions/19884900/how-to-pass-dictionary-from-jinja2-using-python-to-javascript
    recipe_object = (json.dumps(recipe_dict)
    .replace(u'<', u'\\u003c')
    .replace(u'>', u'\\u003e')
    .replace(u'&', u'\\u0026')
    .replace(u"'", u'\\u0027'))

    
    return render_template('index.html',recipe_object=recipe_object)
    
@app.route('/upload', methods=['POST', 'GET'])
def upload():
    
    if request.method == 'POST':
        
        form_picture = request.files['inputFile']
        save_profile_picture(form_picture)
    
    
    
    # db.create_all()
    
    # file = request.files['inputFile']
    # newFile = Filecontents(name=file.filename, data=file.read())
    # db.session.add(newFile)
    # db.session.commit()
    
    return render_template('upload.html')
    
@app.route('/download')
def download():


    return render_template('image-serve-test.html')
    
    
@app.route('/search', methods=['POST', 'GET'])
def search():
    
    search_term = request.form["search"] 
    result = Recipe.query.filter(Recipe.name.contains(search_term))
    
    
    return render_template('search.html', result=result)

if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
            
# add 404 for missing queries http://flask-sqlalchemy.pocoo.org/2.3/queries/#queries-in-views