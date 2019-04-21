import os
from app import *
import unittest
import flask
from flask import url_for, Flask
from flask_testing import TestCase

test_added_recipe = {
                u'name': u'Test-8237629127462193', 
                u'image_file_url': u'86151115.jpg', 
                u'serves': u'1', 
                u'difficulty': u'easy', 
                u'time': u'90', 
                u'method': u'Test'}

test_added_ingredients = {
                    u'1': {
                        u'amount': u'test', 
                        u'ingred': u'testingred2', 
                        u'is_vegetarian': True, 
                        u'is_vegan': True, 
                        u'is_gluten_free': False}, 
                    u'0': {
                        u'amount': u'test', 
                        u'ingred': u'testingred', 
                        u'is_vegetarian': True, 
                        u'is_vegan': False, 
                        u'is_gluten_free': False}}
                        
"""
The test file uses the following database records:
User
username = "testing-account-viewed-recipe"
User
username = "mstonieri"
User
username = "testing-account-not-viewed-recipe"
Recipe
name = "star-pizzas"

viewed_recipe
user = "testing-account-viewed-recipe"
recipe = "star-pizzas"

The following records must not exists:
viewed_recipes
user = "testing-account-not-viewed-recipe"
recipe = "star-pizzas"
"""

class RecipeTests(TestCase):
    
    def create_app(self):

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'
        db.init_app(app)
        
        return app
        
    def setUp(self):
        
        db.create_all()
        

    def tearDown(self):
        
        db.session.remove()
        db.drop_all()
        
    # Test_record_id
    original_result = Recipe.query.filter_by(name='star pizzas').first()
    recipe_id = original_result.id
    global recipe_id
    
    # Test Homepage 200
    def test_home_200_response(self):
        with app.test_client() as client:
            result = client.get("/")
            self.assertEqual(result.status_code, 200)
    
    # Test search page 200
    def test_search_200_response(self):
        with app.test_client() as client:
            result = client.get("/search")
            self.assertEqual(result.status_code, 200)
            
    # Test random recipe page
    def test_recipe_page_200_response(self):
        with app.test_client() as client:
            result = client.get("/recipe/star-pizzas/%s" % (recipe_id))
            self.assertEqual(result.status_code, 200)
            
    # Test register page
    def test_register_200_response(self):
        with app.test_client() as client:
            result = client.get("/register")
            self.assertEqual(result.status_code, 200)
            
    # Test login page
    def test_login_200_response(self):
        with app.test_client() as client:
            result = client.get("/login")
            self.assertEqual(result.status_code, 200)
            
    # Test add recipe page - info
    def test_add_info_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "testing-account-viewed-recipe"
            result = client.get("/add-recipe/info")
            self.assertEqual(result.status_code, 200)
    
    # Test add recipe page - ingredients 
    def test_add_ingredients_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "testing-account-viewed-recipe"
                sess["added_recipe"] = test_added_recipe
            result = client.get("/add-recipe/ingredients")
            self.assertEqual(result.status_code, 200)
    
    # Test add recipe page - submit
    def test_add_submit_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "mstonieri"
                sess["added_recipe"] = test_added_recipe
                sess["added_recipe_ingredients"] = test_added_ingredients
            result = client.get("/add-recipe/submit")
            self.assertEqual(result.status_code, 200)
    
    # Test update recipe page - info
    def test_update_info_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "mstonieri"
            result = client.get("/update-recipe/info/%s" % (recipe_id))
            self.assertEqual(result.status_code, 200)
    
    # Test update recipe page - ingredients 
    def test_update_ingredients_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "mstonieri"
                sess["update_recipe"] = test_added_recipe
            result = client.get("/update-recipe/ingredients/%s" % (recipe_id))
            self.assertEqual(result.status_code, 200)
    
    # Test update recipe page - submit
    def test_update_submit_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "mstonieri"
                sess["update_recipe"] = test_added_recipe
                sess["update_recipe_ingredients"] = test_added_ingredients
            result = client.get("/update-recipe/submit/%s" % (recipe_id))
            self.assertEqual(result.status_code, 200)
            
    # Test user authentication for updating recipes
    
    # Test update recipe page - info
    def test_update_info_incorrect_user_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Incorrect user
                sess["username"] = "testing-account-not-viewed-recipe"
            result = client.get("/update-recipe/info/%s" % (recipe_id))
            self.assertEqual(result.status_code, 302)
            self.assertEqual(result.location, url_for('index', _external=True))
    
    # Test update recipe page - ingredients 
    def test_update_ingredients_incorrect_user_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Incorrect user
                sess["username"] = "testing-account-not-viewed-recipe"
                sess["update_recipe"] = test_added_recipe
            result = client.get("/update-recipe/ingredients/%s" % (recipe_id))
            self.assertEqual(result.status_code, 302)
            self.assertEqual(result.location, url_for('index', _external=True))
    
    # Test update recipe page - submit
    def test_update_submit_incorrect_user_200_response(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Incorrect user
                sess["username"] = "testing-account-not-viewed-recipe"
                sess["update_recipe"] = test_added_recipe
                sess["update_recipe_ingredients"] = test_added_ingredients
            result = client.get("/update-recipe/submit/%s" % (recipe_id))
            self.assertEqual(result.status_code, 302)
            self.assertEqual(result.location, url_for('index', _external=True))
    
    
    """
    When a recipe is viewed for the first time by a registered user, view count
    increases by one
    """
    # View count before view
    original_result = Recipe.query.filter_by(name='star pizzas').first()
    original_result_views = original_result.views
    global original_result_views
    
    def test_view_count_not_viewed(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "testing-account-not-viewed-recipe"
                viewed_recipe = None
            
            # View count after view
            result = client.get("/recipe/star-pizzas/%s" % (recipe_id))
            updated_result = Recipe.query.filter_by(name='star pizzas').first()
            updated_result_views = updated_result.views    
            
            # View count increased by one
            self.assertEqual(updated_result_views - original_result_views,1)
            
            # Reset so test can be ran again
            db.engine.execute('DELETE FROM viewed_recipes WHERE user_ud = 51')
            updated_result.views = updated_result.views - 1
            db.session.commit()
    
    # View count shouldn't change as the user has viewed the recipe before
    original_result = Recipe.query.filter_by(name='star pizzas').first()
    original_result_views = original_result.views
    global original_result_views
            
    def test_view_count_viewed(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["username"] = "testing-account-viewed-recipe"
                viewed_recipe = None
            
            # View count after view
            result = client.get("/recipe/star-pizzas/%s" % (recipe_id))
            updated_result = Recipe.query.filter_by(name='star pizzas').first()
            updated_result_views = updated_result.views    
            
            # View count stays the same
            self.assertEqual(updated_result_views, original_result_views)
            
    # Test upload submit page adds recipe to database
    def test_upload_submit(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:

                sess["username"] = "testing-account-viewed-recipe"
                sess["added_recipe"] = test_added_recipe
                sess["added_recipe_ingredients"] = test_added_ingredients
                
            # Submit recipe to DB
            result = client.post("/add-recipe/submit")

            # Retrieve recipe and test if exists
            self.assertTrue(Recipe.query.filter_by(name=sess["added_recipe"]["name"]).first())
            recipe_id = Recipe.query.filter_by(name=sess["added_recipe"]["name"]).with_entities(Recipe.id)
            recipe_id = recipe_id[0][0]
            
            
            # And delete recipe afterwards so test can be re-run
            Ingredients.query.filter_by(name="testingred").delete()
            Ingredients.query.filter_by(name="testingred2").delete()
            Recipe.query.filter_by(name="Test-8237629127462193").delete()
            db.session.commit()
            delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
            db.engine.execute(delete_str)
            
    # Test update submit updates a recipe in the database
    def test_update_submit(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                
                # Add test recipe to DB
                Recipe_test = Recipe(name=u'TESTINGNAME',
                                     serves= 1,
                                     difficulty=u'easy',
                                     time=90,
                                     views=0,
                                     method=u"Test",
                                     user_id=52,
                                     image_file=u'86151115.jpg')
                Ingredients_test_1 = Ingredients(amount=u'test',
                                     name = u'testingred2',
                                     is_vegetarian=1,
                                     is_vegan=1,
                                     is_gluten_free=1)
                Ingredients_test_2 = Ingredients(amount=u'test',
                                     name = u'testingred',
                                     is_vegetarian=1,
                                     is_vegan=0,
                                     is_gluten_free=0)
                Recipe_test.ingredients.append(Ingredients_test_1)
                Recipe_test.ingredients.append(Ingredients_test_2)
                db.session.add(Recipe_test)
                db.session.add(Ingredients_test_1)
                db.session.add(Ingredients_test_2)
                db.session.commit()
                
            # Created session variables and change name for test
                sess["username"] = "testing-account-viewed-recipe"
                sess["update_recipe"] = {
                    # 
                    u'name': u'NEW NAME', 
                    u'image_file_url': u'86151115.jpg', 
                    u'serves': u'1', 
                    u'difficulty': u'easy', 
                    u'time': u'90', 
                    u'method': u'Test'}
                    
                sess["update_recipe_ingredients"] = {
                    u'1': {
                        u'amount': u'test', 
                        u'ingred': u'testingred2', 
                        u'is_vegetarian': True, 
                        u'is_vegan': True, 
                        u'is_gluten_free': True}, 
                    u'0': {
                        u'amount': u'test', 
                        u'ingred': u'testingred', 
                        u'is_vegetarian': True, 
                        u'is_vegan': False, 
                        u'is_gluten_free': False}}
                

                recipe_id = Recipe.query.filter_by(name="TESTINGNAME").with_entities(Recipe.id)
                recipe_id = recipe_id[0][0]
            
            # Submit updated recipe to DB
            result = client.post("/update-recipe/submit/%s" % recipe_id)

            # Retrieve updated recipe's name
            recipe_name = Recipe.query.filter_by(id=recipe_id).with_entities(Recipe.name)

            # Check if name has been updated successfully
            self.assertEqual("NEW NAME",recipe_name[0][0])

            # Delete recipe so test can be run again
            Recipe.query.filter_by(id=recipe_id).delete()
            Ingredients.query.filter_by(name="testingred").delete()
            Ingredients.query.filter_by(name="testingred2").delete()
            db.session.commit()
            delete_str = "DELETE FROM recipe_ingredients WHERE recipe_id = %s ;" % recipe_id
            db.engine.execute(delete_str)
    
    # Test delete deletes a recipe in the database
    def test_delete_submit(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                
                # Add test recipe to DB
                Recipe_test = Recipe(name=u'TESTINGNAME',
                                     serves= 1,
                                     difficulty=u'easy',
                                     time=90,
                                     views=0,
                                     method=u"Test",
                                     user_id=52,
                                     image_file=u'86151115.jpg')
                Ingredients_test_1 = Ingredients(amount=u'test',
                                     name = u'testingred2',
                                     is_vegetarian=1,
                                     is_vegan=1,
                                     is_gluten_free=1)
                Ingredients_test_2 = Ingredients(amount=u'test',
                                     name = u'testingred',
                                     is_vegetarian=1,
                                     is_vegan=0,
                                     is_gluten_free=0)
                Recipe_test.ingredients.append(Ingredients_test_1)
                Recipe_test.ingredients.append(Ingredients_test_2)
                db.session.add(Recipe_test)
                db.session.add(Ingredients_test_1)
                db.session.add(Ingredients_test_2)
                db.session.commit()
                
                sess["username"] = "testing-account-viewed-recipe"
                
                recipe_id = Recipe.query.filter_by(name='TESTINGNAME').with_entities(Recipe.id)
                recipe_id = recipe_id[0][0]
            
            # Deletes recipe by visisting /delete/<recipe_id>
            result = client.get("/delete/%s" % recipe_id)
            
            # Test to ensure recipe has been deleted
            self.assertFalse(Recipe.query.filter_by(name='TESTINGNAME').first())
            
            
            
if __name__ == "__main__":
    unittest.main()