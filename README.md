# OrderPizzaBoot

### About
A conversational assistant to order pizza

This chatbot was built using [Rasa](https://rasa.com/docs/getting-started/). Tutorials on how to develop a similar chatbot are available on the offical website and also on [Youtube](https://www.youtube.com/watch?v=rlAQWbhwqLA&list=PL75e0qA87dlHQny7z43NduZHPo6qd-cRc)

### Getting Started
> install first [Rasa](https://rasa.com/docs/rasa/user-guide/installation/#installation)


### Train the chatbot
```
rasa train
```

### Test chatbot
```
rasa test
```

### Talk to chatbot
```
rasa shell
```
In case it doesn't predict any response please use specifying the model folder:
```commandline
rasa shell -m models/
```

## Interactive Rasa Tool
No more available for free users
Install first [Rasa X](https://rasa.com/docs/rasa-x/)
```
pip install rasa-x --extra-index-url https://pypi.rasa.com/simple
```

```
rasa x
```
### Create the enviroment
```
conda create --name rasa_env python=3.8
pip install rasa==3.6.13
pip install spacy
python -m spacy download en_core_web_md

pip install "sqlalchemy<2.0"
export SQLALCHEMY_SILENCE_UBER_WARNING=1
```

### Telegram bot
The token is not accessible. But to make it work I run thi commands.
```
ngrok http 5005
rasa run 
rasa run actions
```
