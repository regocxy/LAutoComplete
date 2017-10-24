
function test2.func1( ... )
    -- body

end

function func2( a )
    -- body
end

function func3(a,b)
    -- body
end

func4 = function(a,b ,c)
    print('hello')
end

local func5 = function(a,b ,c)
    print('hello')
end

test2.func6 = function(... )
    print('hello')
end

local function func7( a )
    
end

local function func8( ... )
    -- body
end

print(function() end)

func7()

--not support it now
hello.func8 = func8

print('中文测试')


