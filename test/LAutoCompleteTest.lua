
function test.foo1( ... )
    -- body

end

function foo2( a )
    -- body
end

function foo3(a,b)
    -- body
end

foo4 = function(a,b ,c)
    print('hello')
end

local foo5 = function(a,b ,c)
    print('hello')
end

test.foo6 = function(... )
    print('hello')
end

local function foo7( a )
    
end

local function foo8( ... )
    -- body
end

print(function() end)

foo7()

--not support it now
hello.foo8 = foo8


print('中文测试')



