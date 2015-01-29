import logging
import os

from twitter.common.contextutil import temporary_dir

from pex.common import safe_copy
from pex.fetcher import Fetcher
from pex.resolver import resolve
from pex.testing import make_sdist


class TimingAccruingFilter(logging.Filter):
  def __init__(self):
    import time
    self.t0 = time.time()
    self.t1 = self.t0

  def filter(self, record):
    record.absdelta = int((record.created - self.t0) * 1000)
    record.delta = int((record.created - self.t1) * 1000)
    self.lastdelta = record.delta
    self.t1 = record.created
    return True

DATE_FMT = '%Y%m%d %H:%M:%S'
FORMAT = (
  '%(levelname).1s'  # A single char for the log level ('I', 'W', 'E')
  '%(asctime)s '  # timestamp printed according to DATE_FMT
  '%(absdelta)6s '  #msec from the first log message
  '%(delta)6s '  #msec from the first log message
  '%(filename)s:%(lineno)d '  # the name, line number of the log statement
  '%(message).10000s'  # the log message, limited to 10000 characters for sanity.
)
logging.basicConfig(
  format=FORMAT,
  #datefmt=DATE_FMT,
  level=logging.INFO)
timing_filter = TimingAccruingFilter()
for handler in logging.root.handlers:
  handler.addFilter(timing_filter)


def test_thats_it_thats_the_test():
  empty_resolve = resolve([])
  assert empty_resolve == set()

  with temporary_dir() as td:
    empty_resolve = resolve([], cache=td)
    assert empty_resolve == set()


def test_simple_local_resolve():
  project_sdist = make_sdist(name='project')

  with temporary_dir() as td:
    safe_copy(project_sdist, os.path.join(td, os.path.basename(project_sdist)))
    fetchers = [Fetcher([td])]
    dists = resolve(['project'], fetchers=fetchers)
    assert len(dists) == 1

def test_timings():
  import cProfile, pstats, StringIO
  profiler = cProfile.Profile()
  profiler.enable()
  with temporary_dir() as td:
    n = 100
    timings = [0 for _ in range(n)]
    for i in range(n):
      logging.error('Starting  attempt #%s/%s', i, n)
      fetchers = [Fetcher([td]), Fetcher(['/Users/ugo/.python.install.cache/'])]
      dists = resolve(requirements=['pytz==2013b'], fetchers=fetchers)
      assert len(dists) == 1
      logging.error('Completed attempt #%s/%s', i, n)
      timings[i] = timing_filter.lastdelta

  logging.info('All times in ms: %r', timings)
  logging.info('Mean time: %sms', sum(timings) * 1.0 / len(timings))
  profiler.disable()
  profiler.dump_stats('output.pstats')
  s = StringIO.StringIO()
  sortby = 'cumulative'
  ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
  ps.print_stats()
  print s.getvalue()
  assert False


# TODO(wickman) Test resolve and cached resolve more directly than via
# integration.
