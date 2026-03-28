// 2-stage registered ALU: inputs are latched into a_r/b_r/op_r each
// clock, then the case statement computes from those registers.  Due to
// non-blocking assignment semantics the case reads the OLD register
// values while simultaneously latching NEW inputs — so the result
// appears TWO cycles after inputs are first presented.
// op: 2'b00=ADD  2'b01=SUB  2'b10=AND  2'b11=OR
// Three wiring bugs corrupt the pipeline data flow.
module pipe_alu(
  input  clk,
  input  reset,
  input  [7:0] a_in, b_in,
  input  [1:0] op,
  output reg [7:0] result
);
  reg [7:0] a_r, b_r;
  reg [1:0] op_r;

  always @(posedge clk) begin
    if (reset) begin
      a_r    <= 8'h00;
      b_r    <= 8'h00;
      op_r   <= 2'b00;
      result <= 8'hFF;
    end else begin
      a_r  <= b_in;
      b_r  <= a_in;
      op_r <= op;
      case (op)
        2'b00: result <= a_r + b_r;
        2'b01: result <= a_r - b_r;
        2'b10: result <= a_r & b_r;
        2'b11: result <= a_r | b_r;
      endcase
    end
  end

  p_reset: assert property (@(posedge clk) reset |=> result == 8'h00);
  p_add:   assert property (@(posedge clk) !reset && op==2'b00 && a_in==8'd20 && b_in==8'd7 ##1 !reset |=> reset || result == 8'd27);
  p_sub:   assert property (@(posedge clk) !reset && op==2'b01 && a_in==8'd20 && b_in==8'd7 ##1 !reset |=> reset || result == 8'd13);
  p_and:   assert property (@(posedge clk) !reset && op==2'b10 && a_in==8'hAA && b_in==8'h0F ##1 !reset |=> reset || result == 8'h0A);
  p_or:    assert property (@(posedge clk) !reset && op==2'b11 && a_in==8'hA0 && b_in==8'h0B ##1 !reset |=> reset || result == 8'hAB);
endmodule
