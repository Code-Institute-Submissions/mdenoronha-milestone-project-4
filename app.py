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
    db.Column('measurements_id', db.Integer, db.ForeignKey('measurements.id'))
)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    serves = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(6), nullable=False)
    time = db.Column(db.Integer, nullable=False)
    views = db.Column(db.Integer, nullable=False, default='0')
    method = db.Column(db.Text, nullable=False)
    ingredients = db.relationship('Ingredients', secondary=recipe_ingredients, lazy='subquery',
        backref=db.backref('ingredients', lazy=True))
    measurements = db.relationship('Measurements', secondary=recipe_ingredients, lazy='subquery',
        backref=db.backref('measurements', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
        nullable=False)    

    def __repr__(self):
        return '<Recipe %r>' % (self.id)
            
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
        
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    recipe = db.relationship('Recipe', backref="author", lazy=True)

    def __repr__(self):
        return '<User %r>' % self.username

# # Notes
# db.create_all()
# recipe2 = Recipe(name="conffgue", serves="5", difficulty="hard", time="100",views="2", method="Donec diam neque, vestibulum eget, vulputate ut, ultrices vel, augue. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Donec pharetra, magna vestibulum aliquet ultrices, erat tortor sollicitudin mi, sit amet lobortis sapien sapien non mi. Integer ac neque. Duis bibendum. Morbi non quam nec dui luctus rutrum. Nulla tellus.")

# db.session.add(recipe2)
# db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    
    recipe_text = Recipe.query.all()

     
    return render_template('index.html', recipe_text=recipe_text)

if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
            
# add 404 for missing queries http://flask-sqlalchemy.pocoo.org/2.3/queries/#queries-in-views