from rush.utils.exceptions import NotFoundError

DEFAULT_404 = """\
<style type="text/css" media="screen">
  .container {
    margin: 10px auto;
    max-width: 600px;
    text-align: center;
  }
  h1 {
    margin: 30px 0;
    font-size: 4em;
    line-height: 1;
    letter-spacing: -1px;
  }
</style>

<div class="container">
  <h1>404</h1>

  <p><strong>Page not found :(</strong></p>
  <p>The requested page could not be found.</p>
</div>
"""
DEFAULT_500 = """\
<style type="text/css" media="screen">
  .container {
    margin: 10px auto;
    max-width: 600px;
    text-align: center;
  }
  h1 {
    margin: 30px 0;
    font-size: 4em;
    line-height: 1;
    letter-spacing: -1px;
  }
</style>

<div class="container">
  <h1>500</h1>

  <p><strong>Internal Server Error</strong></p>
  <p>Something is broken on the server</p>
</div>
"""


def not_found(request):
    try:
        request.response_file('404.html')
    except (NotFoundError, FileNotFoundError):
        request.response(404, body=DEFAULT_404)


def internal_error(request):
    try:
        request.response_file('500.html')
    except (NotFoundError, FileNotFoundError):
        request.response(500, body=DEFAULT_500)
