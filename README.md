# EduKona Backend

EduKona is an innovative educational platform that is free and open-source, designed to enrich the learning experience by enabling educators to create customizable educational games tailored to various classroom settings.

## Technology Stack

- **Framework**: Django
- **APIs**: Django REST Framework
- **Database**: PostgreSQL
- **Deployment**: AWS Elastic Beanstalk with automated CI/CD via GitHub Actions
- **Testing**: pytest for Django

## Features

- Create interactive, quiz-based learning modules.
- Real-time graphical analysis of student performance.
- Mobile-friendly design to support learning on any device.

## Getting Started

Visit [EDUKona Live](https://pr21.edukona.com/) to try it live!

### Steps to Use
1. Sign up as an instructor.
2. Create a new quiz.
3. Start your quiz from Home.
4. Have students access [Join Quiz](https://pr21.edukona.com/join) and enter in the quiz code to start a quiz session.

### Prerequisites

- Python 3.8+
- pip
- Virtualenv

### Installation

1. Clone the repository:
   git clone https://github.com/amhajja/hice_backend.git
   cd hice_backend
   
2.Set up a virtual environment:
virtualenv venv
source venv/bin/activate

3.Install the dependencies:
pip install -r requirements.txt

4.Setup the database:
python manage.py migrate

5.Start the server:
python manage.py runserver

## Contributing

Visit our [front-end repo](https://github.com/uncc-hice/edukona_frontend) to view the frontend code!

We welcome contributions from the community, whether it's adding new features, fixing bugs, or improving documentation.

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -am 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a pull request.

Please ensure your commits are small and focused; this makes it easier to review and understand the history.

## Contact

Ayman Hajja - ahajja@charlotte.edu
