import traceback
from hmac import compare_digest

from flask import request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    get_jwt,
)
from flask_restful import Resource
from marshmallow import ValidationError

from blocklist import BLOCKLIST
from models.confirmation import ConfirmationModel
from models.user import UserModel
from schemas.user import UserSchema
from libs.mailgun import MailGunException

USER_ALREADY_EXIST = "Username '{}' already exists."
EMAIL_ALREADY_EXIST = "email '{}' already exists."
USER_NOT_FOUND = "User not found"
USER_DELETED = "User deleted successfully."
INVALID_CREDENTIALS = "Invalid Credentials."
USER_LOGOUT = "User <id={}> successfully logged out."
USER_NOT_CONFIRMED = "user '{}' not confirmed.  Please check your mail id <{email_id}>"
USER_CONFIRMED = "user '{}' confirmed"
FAILED_TO_CREATE = "Internal server error. Failed to create user."
SUCCESS_REGISTER_MESSAGE = "Account created successfully, an email with an activation link has been sent to your registered" \
                           "email address.  Please check."

user_schema = UserSchema()


class UserRegister(Resource):
    @classmethod
    def post(cls):
        try:
            user = user_schema.load(request.get_json())
        except ValidationError as err:
            return err.messages, 400

        username_ = user.username
        if UserModel.find_by_username(username_):
            return {"message": USER_ALREADY_EXIST.format(username_)}, 400

        if UserModel.find_by_email(user.email):
            return {"message": EMAIL_ALREADY_EXIST.format(user.email)}, 400

        try:
            user.save_to_db()
            confirmation = ConfirmationModel(user.id)
            confirmation.save_to_db()
            user.send_confirmation_email()
            return {"message": SUCCESS_REGISTER_MESSAGE}, 201
        except MailGunException as e:
            user.delete_from_db()
            return {"message": str(e)}, 500
        except:
            traceback.print_exc()
            user.delete_from_db()
            return {"message": FAILED_TO_CREATE}, 500


class User(Resource):
    """
    This resource can be useful when testing our Flask app. We may not want to expose it to public users, but for the
    sake of demonstration in this course, it can be useful when we are manipulating data regarding the users.
    """

    @classmethod
    def get(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": USER_NOT_FOUND}, 404
        return user_schema.dump(user), 200

    @classmethod
    def delete(cls, user_id: int):
        user = UserModel.find_by_id(user_id)
        if not user:
            return {"message": USER_NOT_FOUND}, 404
        user.delete_from_db()
        return {"message": USER_DELETED}, 200


class UserLogin(Resource):
    @classmethod
    def post(cls):
        user_data = user_schema.load(request.get_json(), partial=("email",))

        user = UserModel.find_by_username(user_data.username)

        if user and compare_digest(user.password, user_data.password):

            confirmation = user.most_recent_confirmation
            if confirmation and confirmation.confirmed:
                access_token = create_access_token(identity=user.id, fresh=True)
                refresh_token = create_refresh_token(user.id)
                return {"access_token": access_token, "refresh_token": refresh_token}, 200
            else:
                return {"message": USER_NOT_CONFIRMED.format(user.username, email_id=user.username)}, 400

        return {"message": INVALID_CREDENTIALS}, 401


class UserLogout(Resource):
    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]  # jti is "JWT ID", a unique identifier for a JWT.
        user_id = get_jwt_identity()
        BLOCKLIST.add(jti)
        return {"message": USER_LOGOUT.format(user_id)}, 200


class TokenRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {"access_token": new_token}, 200
