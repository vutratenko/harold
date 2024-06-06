<img title="Harold" alt="a brancing service for R1 staging k8s cluster" width=250px
  height=auto src="https://vignette.wikia.nocookie.net/fallout/images/0/0f/FO02_NPC_Harold_G.png/revision/latest?cb=20100812023117">

# harold

Harold - сервис бранчей для кластера stage k8s R1

## Описание
Harold - это система управления DEV окружениями для тестовых кластеров k8s. Она позволяет разворачивать сервисы из ветки в любимой SCM, а зависимости подключать из заранее указанного стабильного (stage) namespace'а посредством добавления в deployment'ы DEV namespace'а собственного контролируемого DNS сервера. 

## Установка
Поставляется в Docker контейнерах и развёртывается посредством helm chart'а, находящегося в директории `helm/harold`. `values.yaml` у чарта более-менее стандартный и видится достаточно очевидным для описания всех полей. Детали можно найти в комментариях к самому файлу.

## Использование
### harold
`GET /branches`
Возвращает список (list) созданных окружений

`POST /branches`
Принимает JSON структуру `{'name': 'имя ветки'}` для создания неймспейса с таким именем. Если такой неймспейс существует, просто обновляет ему значение `last_change_timestamp` на `now()`.

`DELETE /branches`
Принимает JSON структуру `{'name': 'имя ветки'}`, обозначая удаление неймспейса.

### watchman
Не имеет API. Отвечает на DNS запросы. Для своей работы требует добавления структуры, показанной ниже в deployment перед его созданием.

        spec:
          dnsPolicy: "ClusterFirst"
          dnsConfig:
            nameservers:
              - 10.43.92.229 #IP адрес сервиса, стоящего перед pod'ами watchman
            options:
              - name: rotate


## Поддержка
За помощью с сервисом можно обращаться на почту vladimir.utratenko@r1.team

## Дорожная карта
- Тесты
- Аутентификация

## Contributing
Проект открыт для доработок. Все желающие приглашаются присоединиться.
