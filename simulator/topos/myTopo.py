import sim

def launch (switch_type = sim.config.default_switch_type, host_type = sim.config.default_host_type):
    switch_type.create('A')
    switch_type.create('B')
    switch_type.create('C')
    switch_type.create('D')

    host_type.create('h1')
    host_type.create('h2')
    host_type.create('h3')
    host_type.create('h4')

    A.linkTo(B, latency=2)
    B.linkTo(D, latency=3)
    D.linkTo(C)
    C.linkTo(A, latency=7)
    B.linkTo(C)

    h1.linkTo(A)
    h2.linkTo(B)
    h3.linkTo(C)
    h4.linkTo(D)