from flask import Flask, render_template, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recipeapp.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dsaf0897sfdg45sfdgfdsaqzdf98sdf0a'
db = SQLAlchemy(app)

recipe_ingredients = db.Table('recipe_ingredients',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id')),
    db.Column('ingredients_id', db.Integer, db.ForeignKey('ingredients.id')),
    db.Column('measurements_id', db.Integer, db.ForeignKey('measurements.id'), primary_key=True)
)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    serves = db.Column(db.Integer, unique=True, nullable=False)
    difficulty = db.Column(db.String(6), unique=True, nullable=False)
    time = db.Column(db.Integer, unique=True, nullable=False)
    views = db.Column(db.Integer, unique=True, nullable=False)
    # add 0 as standard for below
    method = db.Column(db.Text, unique=True, nullable=False)
    # user = db.relationship('Recipe', backref="author", lazy=True)
    ingredients = db.relationship('Ingredients', secondary=recipe_ingredients, lazy='subquery',
        backref=db.backref('ingredients', lazy=True))
    measurments = db.relationship('Measurements', secondary=recipe_ingredients, lazy='subquery',
        backref=db.backref('measurments', lazy=True))

    def __repr__(self):
        return '<Recipe %r>' % self.name
        

        
class Measurements(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unit = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.String(80), nullable=False)
    
    def __repr__(self):
        return '<Measurements %r>' % self.unit
        
class Ingredients(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_vegetarian = db.Column(db.Boolean, nullable=False)
    is_vegan = db.Column(db.Boolean, nullable=False)
    is_gluten_free = db.Column(db.Boolean, nullable=False)
    
    def __repr__(self):
        return '<Ingredients %r>' % self.name
        
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)

#     def __repr__(self):
#         return '<User %r>' % self.username

db.create_all()

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    # # recipe = Recipe.query.filter_by(name='Test Recipe 2').first()
    # # recipe_name = recipe.id
    recipe1 = Recipe(name="congue eget", serves="5", difficulty="easy", time="120",views="0", method="Morbi porttitor lorem id ligula. Suspendisse ornare consequat lectus. In est risus, auctor sed, tristique in, tempus sit amet, sem. Fusce consequat. Nulla nisl. Nunc nisl. Duis bibendum, felis sed interdum venenatis, turpis enim blandit mi, in porttitor pede justo eu massa. Donec dapibus. Duis at velit eu est congue elementum. In hac habitasse platea dictumst. Morbi vestibulum, velit id pretium iaculis, diam erat fermentum justo, nec condimentum neque sapien placerat ante. Nulla justo. Aliquam quis turpis eget elit sodales scelerisque. Mauris sit amet eros. Suspendisse accumsan tortor quis turpis.")
    db.session.add(recipe1)
    db.session.commit()
     
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
            
# add 404 for missing queries http://flask-sqlalchemy.pocoo.org/2.3/queries/#queries-in-views