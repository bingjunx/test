from django.core.management.base import BaseCommand, CommandError
from wxbot.test import main

class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('--test',
        #     action='store_true',
        #     dest='delete',
        #     default=False,
        #     help='Delete poll instead of closing it')

    def handle(self, *args, **options):
        main()
