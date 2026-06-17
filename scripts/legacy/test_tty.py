import asyncio
async def main():
    p = await asyncio.create_subprocess_exec('docker', 'run', '-t', '--rm', 'ubuntu', 'echo', 'hello', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await p.communicate()
    print(f'OUT: {out}')
asyncio.run(main())
