"""Pass action inputs as arguments without interpolating them into shell code."""
import os
from emdash import main


def arguments(env):
    args=['--mode',env.get('ED_MODE','check'),'--root',env.get('ED_ROOT','.'),
          '--max-bytes',env.get('ED_MAX','2097152'),'--report',env.get('ED_REPORT','emdash-report.json')]
    for key,flag in [('ED_ALL','--all-text'),('ED_ENCODED','--encoded')]:
        value=env.get(key,'false').lower()
        if value not in ('true','false'):raise ValueError(key+' must be true or false')
        if value=='true':args.append(flag)
    for pattern in env.get('ED_EXCLUDE','').splitlines():
        if pattern.strip():args+=['--exclude',pattern.strip()]
    return args


if __name__=='__main__':
    try:args=arguments(os.environ)
    except ValueError as error:raise SystemExit(str(error))
    raise SystemExit(main(args))
