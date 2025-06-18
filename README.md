# 学习通云盘网页部署
**通过获取学习通接口完成的原生HTML本地化网盘项目**  

**如果需要部署到公网上**:

将server.py下的API_BASE_URL变量定义为你的地址,默认为http://localhost:8080

如:API_BASE_URL="http://test.com"

**如果需要修改部署的端口:**

请修改server.py下的

```
uvicorn.run(app, host="0.0.0.0", port=8080)
```
