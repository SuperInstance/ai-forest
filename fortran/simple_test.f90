module simple_mod
  use iso_c_binding
  implicit none
  integer(c_int32_t), save :: global_val = 0
contains
  subroutine set_val(val) bind(c, name="set_val")
    integer(c_int32_t), value :: val
    global_val = val
  end subroutine
  function get_val() bind(c, name="get_val")
    integer(c_int32_t) :: get_val
    get_val = global_val
  end function
end module
