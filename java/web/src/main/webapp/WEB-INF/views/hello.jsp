<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib uri="jakarta.tags.core" prefix="c" %>
<html>
<head>
    <title>Hello</title>
    <link rel="stylesheet" href="${pageContext.request.contextPath}/static/app.css" />
</head>
<body>
<h1>${message}</h1>

<form method="post" action="${pageContext.request.contextPath}/users">
    <input type="text" name="username" placeholder="username" required />
    <input type="text" name="fullName" placeholder="full name" required />
    <button type="submit">Create</button>
</form>

<h2>Users</h2>
<ul>
    <c:forEach var="u" items="${users}">
        <li>${u.id} - ${u.username} (${u.fullName})</li>
    </c:forEach>
</ul>
</body>
</html>
