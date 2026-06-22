# PlanPal

A student calendar web application for planning and scheduling academic events.

## Authors

- Frankie Cole (k24027040)
- Theodore Tsiberopoulos (k22024957)
- Ahmet Deha Kayaturk (k23098721)
- Wazna Alshammari (k23096011)
- Wasif Khan (k23149695)
- Moyondafoluwa Bliss Akinwande (k23153214)
- James Andoh (k24034857)
- Aman Hayer (k23055323)
- Abdallah Batah (k24059084)
- Ashrith Behara (k23010155)

## Deployment

The application is deployed at: http://planpal.pythonanywhere.com

Access Credentials:
- Admin: username = `admin`, password = `admin123`
- Standard User: username = `johndoe`, password = `Password123`

Access the admin panel at: 
- Development: http://localhost:8000/admin/
- Production: http://planpal.pythonanywhere.com/admin/

## Installation and Setup

Install dependencies:
```
$ pip install -r requirements.txt
```

Set up the database:
```
$ python manage.py makemigrations
$ python manage.py migrate
```

Seed the database:
```
$ python manage.py seed
```

Run the development server:
```
$ python manage.py runserver
```

## Running Tests

Django tests and coverage:
```
$ coverage run manage.py test
$ coverage report
```

JavaScript tests and coverage:
```
$ npm install
$ npm test
$ npx jest --coverage
```
    

## Third-Party Source Material

**Django 5.2**
- Purpose: Web framework
- Location: Throughout `student_calendar/` and `time_management/`

**django-widget-tweaks**
- Purpose: Form rendering in templates
- Location: `requirements.txt`

**django-with-asserts**
- Purpose: HTML assertion helpers in tests
- Location: `student_calendar/tests/test_utility.py`

**coverage.py**
- Purpose: Django test coverage reporting
- Location: `requirements.txt`

**Jest**
- Purpose: JavaScript unit testing
- Location: `package.json`, `static/js/*.test.js`

**jest-environment-jsdom**
- Purpose: DOM simulation for Jest
- Location: `package.json`

**Google Fonts (Roboto)**
- Purpose: Typography
- Location: `static/css/`

**Small Group Project Codebase**
- Purpose: Login/Sign up authentication system
- Location: student_calendar/views/(`log_in_view.py`, `signup_view.py`, `log_out_view.py`, `decorators.py`), `log_in_form.py`, and all unit tests from above


### Generative AI tools (Claude, ChatGPT)

**Purposes:**

*Code refactoring and debugging*
- Location: `student_calendar/views/`, `student_calendar/models/`, `static/js/`
- Estimated proportion: less than 30% of the refactoring work.

AI was used to identify areas where functions exceeded length or nesting limits, locate dead code and unused variables, and suggest refactoring approaches. 

AI was used to understand parts of teammate code that were otherwise hard to understand.

All suggested changes were reviewed, tested, and committed manually.

*CSS styling assistance*
- Location: `static/css/`
- Estimated proportion: less than 35% of CSS work.

AI was used to assist with layout adjustments, consistency fixes, and resolving styling issues across multiple CSS files.

*HTML templating*
- Location: `student_calendar/templates/`
- Estimated proportion: less than 40% of the templating work.

AI was used to iterate on markup structure, construct basic layouts, and template partial composition.

*Code writing assistance*
- `static/js/smart_planner.js` - 30-50%
- `static/js/statistics.js` - 30%
- `static/js/add-event.js` - 30-45%
- `student_calendar/views/create_event.py` - 30-45%
- `student_calendar/views/user_details.py` - 5-10%

AI was used occasionally to clarify Django-specific behaviour (e.g., form handling and view logic) and assist with minor debugging. All implementation and design decisions were completed independently.

*Test writing assistance*
- `test_statistics_service.py` - 20%
- `test_statistics.py` - 10%
- `test_edit_event.py` — 10% (lines 181–199)
- `test_create_event_form.py` - 30-45%
- `test_create_event.py` - 30-45%
- `test_user_details_view.py` - 20%

AI was used to refine understanding of test structure and edge cases, but all tests were written and validated independently.

*Nix flake configuration and testing*
- Location: `flake.nix`
- Estimated proportion: 70% (structure + package selection), 30% written (entry points)

Nix flake configuration. Initial structure and package selection generated via Claude (claude.ai); application entry points (apps.run, apps.tests, etc.) written for this project.
