from kaggle_environments import make

env = make("lux_ai_2021", configuration={"seed": 562124210, "loglevel": 2, "annotations": True}, debug=True)

steps = env.run(["simple_agent", "simple_agent"])

env.render(mode="ipython", width=1200, height=800)