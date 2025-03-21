import cli2


def test_log_parse():
    logs = '''

name: tes2980898zzzyzy7
 method=POST url=http://localhost:8000/objects/ event=request level=debug timestamp=2025-03-21 10:09:40

data: {}
id: 103
name: tes2980898zzzyzy7
 method=POST url=http://localhost:8000/objects/ status_code=201 event=response level=info timestamp=2025-03-21 10:09:40
event=bogus level=info

name: tes2980898zzzyzy7
 method=POST url=http://localhost:8000/objects/ event=request level=debug timestamp=2025-03-21 10:09:40

name:
- object with this name already exists.
 method=POST url=http://localhost:8000/objects/ status_code=400 event=response level=info timestamp=2025-03-21 10:09:40
    '''

    result = cli2.parse(logs)
    assert result == [
		{
		  'request': {
			  'event': 'request',
			  'json': {
				  'name': 'tes2980898zzzyzy7',
			  },
			  'level': 'debug',
			  'method': 'POST',
			  'timestamp': '2025-03-21 10:09:40',
			  'url': 'http://localhost:8000/objects/',
		  },
		  'response': {
			  'event': 'response',
			  'json': {
				  'data': {},
				  'id': 103,
				  'name': 'tes2980898zzzyzy7',
			  },
			  'level': 'info',
			  'method': 'POST',
			  'status_code': '201',
			  'timestamp': '2025-03-21 10:09:40',
			  'url': 'http://localhost:8000/objects/',
		  },
		},
        {
          'event': 'bogus',
          'level': 'info',
        },
		{
		  'request': {
			  'event': 'request',
			  'json': {
				  'name': 'tes2980898zzzyzy7',
			  },
			  'level': 'debug',
			  'method': 'POST',
			  'timestamp': '2025-03-21 10:09:40',
			  'url': 'http://localhost:8000/objects/',
		  },
		  'response': {
			  'event': 'response',
			  'json': {
				  'name': [
					  'object with this name already exists.',
				  ],
			  },
			  'level': 'info',
			  'method': 'POST',
			  'status_code': '400',
			  'timestamp': '2025-03-21 10:09:40',
			  'url': 'http://localhost:8000/objects/',
		  },
		},
  	]
