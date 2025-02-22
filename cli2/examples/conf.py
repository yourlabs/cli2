import cli2

cli2.cfg.questions['FOO'] = 'What is your FOO?'

print(f'Foo={cli2.cfg["FOO"]}')
print(f'Bar={cli2.cfg["BAR"]}')
