from setuptools import setup

setup(
	name='daniel_authenticator_web',
	version='0.0',
	url='Not public',
	license='AGPL',
	packages=['daniel_authenticator_web'],
	package_data={'daniel_authenticator_web': ['templates/*', 'static/*']},
	include_package_data=True,
	scripts = [
		'daniel-authenticator-connector'
	],
	entry_points = {
		'console_scripts': [
			'daniel-authenticator-cli = daniel_authenticator_web.cli_interface:main',
		]
	}
)

